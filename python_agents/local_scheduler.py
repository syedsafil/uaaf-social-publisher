"""
UAAF LOCAL SCHEDULER — FIXED TIMEZONE + AUTO PUBLISH
═══════════════════════════════════════════════════════════════
Har 30 second baad schedule check karta hai.
Jab time aaye → video publish karta hai (real ya simulated).

LOCAL TEST:
  cd python_agents
  python local_scheduler.py
═══════════════════════════════════════════════════════════════
"""
import os
import sys
import json
import time
import asyncio
from datetime import datetime, date, timezone, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from utils.logger import log

SCHEDULE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "schedule.json")
AUTO_RUN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "auto_generation.json")
CHECK_INTERVAL = 30


ROOT_SCHEDULE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "schedule.json")


def load_schedule():
    """Load schedule.json and safely sync any newly scheduled videos from cloud dashboard"""
    schedules = []
    if os.path.exists(SCHEDULE_FILE):
        try:
            with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
                schedules = json.load(f)
        except Exception:
            pass

    existing_ids = {s.get("id") for s in schedules if s.get("id")}
    existing_titles = {s.get("title", "").strip().lower() for s in schedules if s.get("title")}
    published_titles = {
        s.get("title", "").strip().lower()
        for s in schedules
        if s.get("status") in {"published", "already_published"}
    }

    # Sync newly scheduled videos from Vercel Cloud API
    try:
        import httpx
        cloud_url = "https://uaaf-automation.vercel.app/api/schedule"
        r = httpx.get(cloud_url, timeout=3.5)
        if r.status_code == 200:
            cloud_schedules = r.json().get("schedule", [])
            new_synced = False
            for cs in cloud_schedules:
                cs_id = cs.get("id")
                cs_title = cs.get("title", "").strip().lower()
                cs_path = cs.get("video_path", "")
                if cs.get("status") == "scheduled" and cs_path and cs_path != "uploaded_short.mp4":
                    if cs_id not in existing_ids and cs_title not in existing_titles and cs_title not in published_titles:
                        schedules.insert(0, cs)
                        existing_ids.add(cs_id)
                        existing_titles.add(cs_title)
                        new_synced = True
            if new_synced:
                save_schedule(schedules)
    except Exception:
        pass

    # Clean and deduplicate local list
    clean = []
    seen = set()
    for s in schedules:
        vid = s.get("id")
        if not vid or vid in seen:
            continue
        if s.get("video_path") == "uploaded_short.mp4":
            continue
        seen.add(vid)
        clean.append(s)

    return clean


def save_schedule(schedules):
    """Save to both python_agents/output/schedule.json and output/schedule.json, sync to schedule-store.ts and Vercel cloud"""
    for fpath in [SCHEDULE_FILE, ROOT_SCHEDULE_FILE]:
        try:
            os.makedirs(os.path.dirname(fpath), exist_ok=True)
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(schedules, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log.warn(f"Failed writing {fpath}: {e}")

    # Auto-sync to src/lib/schedule-store.ts for permanent Vercel deployment retention
    try:
        ts_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "lib", "schedule-store.ts")
        if os.path.exists(ts_path):
            with open(ts_path, "r", encoding="utf-8") as f:
                ts_content = f.read()
            s_marker = "export let memorySchedule: ScheduleItem[] = "
            e_marker = "export async function readSchedule"
            s_idx = ts_content.find(s_marker)
            e_idx = ts_content.find(e_marker)
            if s_idx != -1 and e_idx != -1:
                json_str = json.dumps(schedules, indent=2, ensure_ascii=False)
                new_ts_content = ts_content[:s_idx + len(s_marker)] + json_str + ";\n\n" + ts_content[e_idx:]
                with open(ts_path, "w", encoding="utf-8") as f:
                    f.write(new_ts_content)
    except Exception as e:
        log.warn(f"Failed updating schedule-store.ts: {e}")

    # Auto-sync to Vercel cloud API
    try:
        import httpx
        httpx.put("https://uaaf-automation.vercel.app/api/schedule", json={"schedule": schedules}, timeout=8.0)
    except Exception:
        pass

    # Auto-deploy to Vercel production in background for permanent 24/7 cloud persistence
    try:
        import subprocess
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        subprocess.Popen("npx vercel --prod --yes", cwd=root_dir, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log.info("  🚀 [CLOUD SYNC] Automatic background Vercel deployment triggered successfully!")
    except Exception as v_err:
        log.warn(f"Failed triggering automatic Vercel deploy: {v_err}")


async def maybe_run_auto_generation():
    """Generate only once on a day that has no user-uploaded video."""
    now = datetime.now()
    today = now.date().isoformat()
    if now.strftime("%H:%M") < Config.AUTO_GENERATE_TIME:
        return

    schedules = load_schedule()
    if any(item.get("scheduled_date", "")[:10] == today and item.get("status") in {"scheduled", "partially_published", "published"} for item in schedules):
        return

    try:
        with open(AUTO_RUN_FILE, "r", encoding="utf-8") as f:
            if json.load(f).get("date") == today:
                return
    except (OSError, json.JSONDecodeError):
        pass

    log.info("🤖 No user upload today — starting one automatic premium video cycle")
    # Delayed import avoids a module cycle: main imports scheduler, which uses
    # this local scheduler for publication bookkeeping.
    from main import run_autonomous_cycle
    result = await run_autonomous_cycle()
    with open(AUTO_RUN_FILE, "w", encoding="utf-8") as f:
        json.dump({"date": today, "result": result.get("status")}, f)


def check_due_videos():
    """
    Check if any scheduled video's time has arrived.
    STRICT RULE: Only items with status == 'scheduled' can ever be published.
    Once a video has been published, it is NEVER published again.
    """
    schedules = load_schedule()
    due = []
    now = datetime.now()  # LOCAL time — matches what user sets in dashboard

    # Track all already published titles and filenames to prevent any re-publishing
    already_published_titles = {
        s.get("title", "").strip().lower()
        for s in schedules
        if s.get("status") in {"published", "already_published"}
    }
    already_published_files = {
        os.path.basename(s.get("video_path", "")).strip().lower()
        for s in schedules
        if s.get("status") in {"published", "already_published"} and s.get("video_path")
    }

    now_utc = datetime.now(timezone.utc)

    for item in schedules:
        status = item.get("status")

        # 1. Check retry candidates (failed or partially_published with next_retry_at passed)
        if status in {"failed", "partially_published"}:
            next_retry_at = item.get("next_retry_at")
            if next_retry_at:
                try:
                    retry_dt = datetime.fromisoformat(next_retry_at)
                    if now_utc >= retry_dt:
                        due.append(item)
                        log.info(f"  → DUE FOR RETRY: '{item.get('title')}' (scheduled retry attempt {item.get('publish_attempts', 0) + 1})")
                except Exception as e:
                    log.warn(f"Invalid next_retry_at format for '{item.get('title')}': {next_retry_at} ({e})")
            continue

        # 2. Process newly scheduled items
        if status != "scheduled":
            continue

        item_title = item.get("title", "").strip().lower()
        item_fname = os.path.basename(item.get("video_path", "")).strip().lower()

        # Guard: If this exact video was already published previously, skip and mark already_published
        if item_title in already_published_titles or (item_fname and item_fname != "uploaded_short.mp4" and item_fname in already_published_files):
            log.warn(f"⚠️ Video '{item.get('title')}' is ALREADY published! Marking already_published to prevent re-posting.")
            item["status"] = "already_published"
            update_schedule_item(item)
            continue

        scheduled_date = item.get("scheduled_date", "")
        scheduled_time = item.get("scheduled_time", "09:00")

        if not scheduled_date:
            continue

        scheduled_date = scheduled_date[:10]

        try:
            scheduled_dt = datetime.strptime(
                f"{scheduled_date} {scheduled_time}",
                "%Y-%m-%d %H:%M"
            )
        except ValueError:
            log.warn(f"Invalid date/time for '{item.get('title')}': {scheduled_date} {scheduled_time}")
            continue

        # Check if scheduled time has passed
        if now >= scheduled_dt:
            due.append(item)
            log.info(f"  → DUE: '{item['title']}' (scheduled: {scheduled_date} {scheduled_time})")

    return due


async def publish_video_locally(video_data):
    """
    Publish a video locally.
    If API keys set → REAL publish.
    If not → Simulation (shows what would happen).
    """
    log.info("=" * 60)
    log.info(f"🚀 PUBLISHING: {video_data['title']}")
    log.info(f"   Video: {video_data.get('video_path', 'N/A')}")
    log.info(f"   Keyword: {video_data.get('comment_keyword', 'KIT')}")
    log.info(f"   Prompt to send: {video_data.get('prompt_to_send', 'N/A')[:50]}...")
    log.info("=" * 60)

    video_path = video_data.get("video_path", "")
    title = video_data.get("title", "Untitled")
    caption = video_data.get("caption", "")
    hashtags = video_data.get("hashtags", [])

    # Check video file
    if not video_path or not os.path.exists(video_path):
        fname = os.path.basename(video_path) if video_path else ""
        possible_dirs = [
            os.path.join(os.path.dirname(__file__), "output", "uploads"),
            os.path.join(os.path.dirname(__file__), "output"),
            os.path.join(os.path.dirname(__file__), "assets", "videos"),
            os.path.join(os.path.expanduser("~"), "Downloads"),
            os.path.join(os.path.expanduser("~"), "Videos"),
            os.path.join(os.path.expanduser("~"), "Desktop"),
            r"D:\Downloads",
            r"D:\Videos",
            r"D:\D drive folder",
            r"D:\\",
            r"C:\Downloads",
        ]
        import string
        for _drv in string.ascii_uppercase:
            for _sub in ["Downloads", "Videos"]:
                _d_path = f"{_drv}:\\{_sub}"
                if os.path.exists(_d_path) and _d_path not in possible_dirs:
                    possible_dirs.append(_d_path)

        resolved = False
        for d in possible_dirs:
            candidate = os.path.join(d, fname)
            if fname and os.path.exists(candidate):
                video_path = candidate
                resolved = True
                break

        # Fuzzy match if exact name has emoji variations or slight difference
        if not resolved and (fname or title):
            import re
            clean_search = re.sub(r'[^a-zA-Z0-9]', '', fname or title)[:18].lower()
            for d in possible_dirs:
                if os.path.exists(d):
                    try:
                        for f in os.listdir(d):
                            clean_f = re.sub(r'[^a-zA-Z0-9]', '', f).lower()
                            if clean_search and clean_search in clean_f and f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
                                candidate = os.path.join(d, f)
                                if os.path.exists(candidate):
                                    video_path = candidate
                                    resolved = True
                                    clean_f_name = f.encode('ascii', 'replace').decode()
                                    log.info(f"   [Fuzzy Resolved Video File]: {clean_f_name}")
                                    break
                    except Exception:
                        pass
                if resolved:
                    break

        # Deep walk on D: drive if still not resolved anywhere else
        if not resolved and os.path.exists("D:\\"):
            import re
            clean_search = re.sub(r'[^a-zA-Z0-9]', '', fname or title)[:18].lower()
            try:
                for root, dirs, files in os.walk("D:\\"):
                    dirs[:] = [d for d in dirs if not d.startswith('$') and d != 'System Volume Information']
                    for f in files:
                        if fname and f.lower() == fname.lower():
                            video_path = os.path.join(root, f)
                            resolved = True
                            break
                        clean_f = re.sub(r'[^a-zA-Z0-9]', '', f).lower()
                        if clean_search and clean_search in clean_f and f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
                            video_path = os.path.join(root, f)
                            resolved = True
                            break
                    if resolved:
                        clean_f_name = os.path.basename(video_path).encode('ascii', 'replace').decode()
                        log.info(f"   [D-Drive Deep Walk Resolved]: {clean_f_name}")
                        break
            except Exception:
                pass

        if not resolved and not os.path.exists(video_path):
            log.error(f"❌ Video file not found: {video_path}")
            video_data["status"] = "failed"
            video_data["error"] = f"Video file not found: {video_path}"
            return {"status": "failed", "error": "Video file not found"}

    # Check API keys
    has_meta = bool(Config.META_ACCESS_TOKEN and not Config.META_ACCESS_TOKEN.startswith("your_"))
    has_tiktok = bool(Config.TIKTOK_ACCESS_TOKEN and not Config.TIKTOK_ACCESS_TOKEN.startswith("your_"))
    has_youtube = bool(Config.YOUTUBE_REFRESH_TOKEN and not Config.YOUTUBE_REFRESH_TOKEN.startswith("your_"))
    has_x = bool(Config.X_API_KEY and not Config.X_API_KEY.startswith("your_"))

    log.info(f"   Platform Status:")
    log.info(f"     Instagram: {'✅ Connected' if has_meta else '❌ Not configured'}")
    log.info(f"     Facebook:  {'✅ Connected' if has_meta else '❌ Not configured'}")
    log.info(f"     TikTok:    {'✅ Connected' if has_tiktok else '❌ Not configured'}")
    log.info(f"     YouTube:   {'✅ Connected' if has_youtube else '❌ Not configured'}")
    log.info(f"     X.com:     {'✅ Connected' if has_x else '❌ Not configured'}")

    if not any([has_meta, has_tiktok, has_youtube, has_x]):
        log.warn("⚠️  NO PLATFORMS CONNECTED — running simulation")
        log.info("")
        log.info("📋 WHAT WOULD HAPPEN IF KEYS WERE SET:")
        log.info(f"   1. Upload video to: Instagram, Facebook, TikTok, YouTube, X.com")
        log.info(f"   2. Title: {title}")
        log.info(f"   3. Caption: {caption[:60]}...")
        log.info(f"   4. Hashtags: {hashtags}")
        log.info(f"   5. Comment Keyword: {video_data.get('comment_keyword', 'KIT')}")
        log.info(f"   6. Prompt to DM: {video_data.get('prompt_to_send', 'N/A')[:60]}...")
        log.info(f"   7. End screen in video: 'COMMENT {video_data.get('comment_keyword', 'KIT')}'")
        log.info(f"   8. Email to: {Config.CHAIRMAN_EMAIL or 'N/A'}")
        log.info("")
        log.info("✅ SIMULATION COMPLETE")

        video_data["status"] = "credentials_missing"
        video_data["simulated_at"] = datetime.now(timezone.utc).isoformat()
        return {"status": "credentials_missing", "error": "No platform credentials configured in .env", "video_data": video_data}

    # REAL PUBLISH. On a retry, only failed platforms are attempted again so
    # already-live posts are never duplicated.
    try:
        from publish.publish_all import publish_to_all
        previous = video_data.get("published_platforms", {})
        retry_platforms = [
            name for name, result in previous.items()
            if result.get("status") in ("failed", "timed_out", "pending")
        ]
        results = await publish_to_all(
            video_path=video_path,
            caption=caption,
            title=title,
            hashtags=hashtags,
            thumbnail_path=video_data.get("thumbnail_path") or video_data.get("thumbnail_url"),
            platforms=retry_platforms or None,
            comment_keyword=video_data.get("comment_keyword", "NEXT"),
            video_id=video_data.get("id", ""),
        )
        merged_results = {**previous, **results}

        # Categorize platform statuses accurately
        succeeded = [name for name, r in merged_results.items() if r.get("status") == "success"]
        inbox_staged = [name for name, r in merged_results.items() if r.get("status") == "uploaded_to_inbox"]
        pending = [name for name, r in merged_results.items() if r.get("status") == "pending"]
        timed_out = [name for name, r in merged_results.items() if r.get("status") == "timed_out"]
        failed = [name for name, r in merged_results.items() if r.get("status") == "failed"]
        skipped = [name for name, r in merged_results.items() if r.get("status") == "skipped"]

        unresolved = failed + timed_out

        video_data["published_at"] = datetime.now(timezone.utc).isoformat()
        video_data["published_platforms"] = merged_results
        video_data["skipped_platforms"] = skipped
        video_data["publish_attempts"] = int(video_data.get("publish_attempts", 0)) + 1

        # Determine job status based on comprehensive platform outcomes
        if unresolved:
            video_data["failed_platforms"] = unresolved
            if succeeded or inbox_staged:
                video_data["status"] = "partially_published"
                if video_data["publish_attempts"] < 3:
                    retry_time = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
                    video_data["next_retry_at"] = retry_time
                    log.warn(f"⚠️ Partially published: live={succeeded}, inbox={inbox_staged}, unresolved={unresolved}. Scheduled retry at {retry_time} (attempt {video_data['publish_attempts']}/3)")
                else:
                    video_data.pop("next_retry_at", None)
                    log.error(f"⚠️ Max attempts reached for partial publish. Remaining unresolved: {unresolved}")
            else:
                video_data["status"] = "failed"
                if video_data["publish_attempts"] < 3:
                    retry_time = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
                    video_data["next_retry_at"] = retry_time
                    log.warn(f"❌ Publication failed for: {unresolved}. Scheduled retry at {retry_time} (attempt {video_data['publish_attempts']}/3)")
                else:
                    video_data["status"] = "permanently_failed"
                    video_data.pop("next_retry_at", None)
                    log.error(f"❌ Max attempts reached for: {unresolved}. Marked as permanently_failed.")
        elif pending:
            video_data["pending_platforms"] = pending
            if succeeded or inbox_staged:
                video_data["status"] = "partially_published"
            else:
                video_data["status"] = "pending"
            if video_data["publish_attempts"] < 3:
                retry_time = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
                video_data["next_retry_at"] = retry_time
                log.info(f"⏳ Publication pending for: {pending}. Scheduled re-check at {retry_time}")
            else:
                video_data.pop("next_retry_at", None)
        elif inbox_staged and not succeeded:
            # Only inbox staged platforms were targeted
            video_data["status"] = "uploaded_to_inbox"
            video_data["inbox_platforms"] = inbox_staged
            video_data.pop("failed_platforms", None)
            video_data.pop("next_retry_at", None)
            video_data.pop("pending_platforms", None)
            log.info(f"📥 Video uploaded to Creator Inbox on: {inbox_staged}")
        elif inbox_staged and succeeded:
            # Mixed: some live on feed, some in creator inbox
            video_data["status"] = "partially_published"
            video_data["inbox_platforms"] = inbox_staged
            video_data["live_platforms"] = succeeded
            video_data.pop("failed_platforms", None)
            video_data.pop("next_retry_at", None)
            video_data.pop("pending_platforms", None)
            log.info(f"⚠️ Mixed publication: {succeeded} live on feed, {inbox_staged} staged in Creator Inbox")
        elif succeeded:
            # All attempted channels succeeded live
            video_data["status"] = "published"
            video_data.pop("failed_platforms", None)
            video_data.pop("next_retry_at", None)
            video_data.pop("pending_platforms", None)
            video_data.pop("inbox_platforms", None)
            log.info(f"✅ Successfully published live on all platforms: {succeeded}")
        elif skipped:
            video_data["status"] = "skipped"
        else:
            video_data["status"] = "failed"
            video_data["failed_platforms"] = ["unknown"]

        # Email notification
        try:
            from notify.email_approver import send_approval_email
            if Config.RESEND_API_KEY and Config.CHAIRMAN_EMAIL:
                await send_approval_email(
                    creative_id=video_data.get("id", "local"),
                    title=f"{video_data['status'].upper()}: {title}",
                    niche="User Upload",
                    hook=video_data.get("hook", ""),
                    caption=caption,
                    thumbnail_url="",
                    video_url=video_path,
                    quality_score=100 if not failed else 50,
                    predicted_views=0,
                )
                log.info("📧 Email notification sent!")
        except Exception as e:
            log.warn(f"Email notification skipped: {e}")

        log.info(f"Publication result: status={video_data['status']} ({len(succeeded)} live, {len(failed)} failed, {len(skipped)} skipped)")
        return {"status": video_data["status"], "results": merged_results}

    except Exception as e:
        log.error(f"❌ Publish failed: {e}")
        video_data["status"] = "failed"
        return {"status": "failed", "error": str(e)}


def update_schedule_item(updated_item):
    """Update schedule.json entry, prepending if new and sync to Vercel cloud"""
    schedules = load_schedule()
    found = False
    for i, item in enumerate(schedules):
        if item.get("id") == updated_item.get("id"):
            schedules[i] = updated_item
            found = True
            break
    if not found:
        schedules.insert(0, updated_item)
    save_schedule(schedules)


def is_item_waiting(item):
    # ONLY strictly scheduled videos that have NOT been published yet are waiting
    return item.get("status") == "scheduled"


def format_time_remaining(scheduled_date, scheduled_time):
    try:
        dt = datetime.strptime(f"{str(scheduled_date)[:10]} {scheduled_time}", "%Y-%m-%d %H:%M")
        diff = dt - datetime.now()
        if diff.total_seconds() <= 0:
            return "READY TO PUBLISH (Due Now)"
        hours, remainder = divmod(int(diff.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"In {hours}h {minutes}m"
        return f"In {minutes}m {seconds}s"
    except Exception:
        return "Waiting..."


def print_live_dashboard(schedules):
    now_str = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    waiting = [s for s in schedules if is_item_waiting(s)]
    published = [s for s in schedules if not is_item_waiting(s)]

    print("\n" + "=" * 70)
    print("  VISION VAULT / UAAF - 5-PLATFORM LIVE SCHEDULER")
    print("=" * 70)
    print(f"  STATUS        : [ONLINE] Monitoring Active")
    print(f"  SERVICES      : [1] 5-Platform Auto-Publisher  [2] 24/7 Comment & DM Engine")
    print(f"  LOCAL TIME    : {now_str}")
    print(f"  TOTAL VIDEOS  : {len(schedules)}  |  [PUBLISHED]: {len(published)}  |  [WAITING]: {len(waiting)}")
    print("-" * 70)

    if waiting:
        print("  >> UPCOMING VIDEOS TO PUBLISH:")
        for idx, item in enumerate(waiting, 1):
            t_rem = format_time_remaining(item.get("scheduled_date", ""), item.get("scheduled_time", "09:00"))
            clean_title = item.get("title", "Untitled").encode("ascii", "ignore").decode()
            print(f"    [{idx}] \"{clean_title}\"")
            print(f"        Scheduled For : {item.get('scheduled_date')} at {item.get('scheduled_time')} ({t_rem})")
            print(f"        Keyword to DM : #{item.get('comment_keyword', 'KIT')}")
            print(f"        Target        : Instagram, YouTube, TikTok, Facebook, X")
    else:
        print("  >> UPCOMING VIDEOS: Koi video waiting mein nahi hai.")
        print("     (Dashboard se jab bhi new video schedule karenge, woh foran yahan show ho jayegi)")

    print("-" * 70)
    if published:
        print("  >> COMPLETED & PUBLISHED HISTORY:")
        for idx, item in enumerate(published[:3], 1):
            clean_title = item.get("title", "Untitled").encode("ascii", "ignore").decode()
            pub_at = (item.get("published_at") or "")[:19].replace("T", " ")
            print(f"    [{idx}] \"{clean_title}\" (Status: PUBLISHED {pub_at})")
    print("=" * 70)
    print("  [HEARTBEAT] Checking every 30s... (To STOP, bas is window ko Close [X] kar dein)\n")


async def run_scheduler():
    """
    Main loop — checks every 30 seconds and shows live dashboard.
    """
    loop_count = 0

    while True:
        try:
            schedules = load_schedule()
            
            # Print dashboard every 2 minutes (every 4 loops) or on first run
            if loop_count % 4 == 0:
                print_live_dashboard(schedules)
            else:
                ts = datetime.now().strftime("%I:%M:%S %p")
                waiting_count = sum(1 for s in schedules if is_item_waiting(s))
                print(f"  [{ts}] [CHECK] Checked schedule. {waiting_count} video(s) waiting. Next check in 30s...", flush=True)

            due = check_due_videos()
            for video in due:
                clean_title = video.get("title", "Untitled").encode("ascii", "ignore").decode()
                print(f"\n[START] TIME ARRIVED! PUBLISHING NOW: \"{clean_title}\" across 5 platforms...")
                result = await publish_video_locally(video)
                update_schedule_item(video)
                print(f"   -> Finished! Status: {result.get('status', 'unknown')}\n")
                # Immediately show refreshed dashboard after publish
                print_live_dashboard(load_schedule())

            # ── 24/7 AUTO-COMMENT & DM ENGINE (INSTAGRAM, FACEBOOK, YOUTUBE) ──
            try:
                from webhook.auto_comment_worker import poll_instagram, poll_facebook, poll_youtube
                await asyncio.gather(
                    poll_instagram(),
                    poll_facebook(),
                    poll_youtube(),
                    return_exceptions=True
                )
            except Exception as poller_err:
                log.warn(f"Auto-comment/DM poller error: {poller_err}")

            loop_count += 1
        except KeyboardInterrupt:
            print("\n👋 Auto-Scheduler stopped by user.")
            break
        except Exception as e:
            log.error(f"Error: {e}")

        await asyncio.sleep(CHECK_INTERVAL)


import socket
_lock_socket = None

def acquire_singleton_lock(port=49872):
    global _lock_socket
    try:
        _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _lock_socket.bind(("127.0.0.1", port))
        _lock_socket.listen(1)
        return True
    except socket.error:
        return False

if __name__ == "__main__":
    if not acquire_singleton_lock():
        log.warn("⚠️ UAAF Auto-Scheduler is ALREADY running in the background! Exiting duplicate instance to prevent double-posting.")
        sys.exit(0)
    try:
        asyncio.run(run_scheduler())
    except KeyboardInterrupt:
        print("\n👋 Stopped.")
