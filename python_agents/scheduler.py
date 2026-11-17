"""
UAAF VIDEO SCHEDULER — FIXED TIMEZONE SYNC
═══════════════════════════════════════════════════════════════
FIX: Date/time parsing now uses LOCAL timezone (not UTC mismatch)
═══════════════════════════════════════════════════════════════
"""
import os
import sys
import json
import asyncio
from datetime import datetime, date, timezone, timedelta
from typing import List, Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from utils.logger import log


async def check_today_schedule():
    """
    Check if there's a user-uploaded video scheduled for today.
    FIXED: Uses LOCAL date (not UTC) to match dashboard input.
    """
    # Use LOCAL date — user sets date in their timezone on dashboard
    today = date.today().isoformat()
    log.info(f"Scheduler: checking for scheduled videos on {today} (local time)")

    schedule_file = os.path.join(Config.OUTPUT_DIR, "schedule.json")

    if os.path.exists(schedule_file):
        with open(schedule_file, "r", encoding="utf-8") as f:
            schedules = json.load(f)

        for item in schedules:
            if item.get("status") != "scheduled":
                continue

            item_date = item.get("scheduled_date", "")
            if not item_date:
                continue

            # Normalize date format (strip any timezone info)
            item_date = item_date[:10]  # YYYY-MM-DD only

            scheduled_time = item.get("scheduled_time", "09:00")
            try:
                due_at = datetime.strptime(f"{item_date} {scheduled_time}", "%Y-%m-%d %H:%M")
            except ValueError:
                log.warn(f"  Invalid scheduled time: {scheduled_time}")
                continue

            if item_date == today and datetime.now() >= due_at:
                video_path = item.get("video_path", "")
                if video_path and os.path.exists(video_path):
                    log.info(f"  Found scheduled video: {item['title']}")
                    log.info(f"  Scheduled time: {item.get('scheduled_time', '09:00')}")
                    return {"mode": "user_upload", "video": item}
                else:
                    log.warn(f"  Scheduled video file missing: {video_path}")

    log.info("  No user-uploaded video scheduled for today — will auto-generate")
    return {"mode": "auto_generate"}


async def publish_scheduled_video(video_data: Dict):
    """Publish without ever reporting a partial result as fully published."""
    from local_scheduler import publish_video_locally

    log.info(f"Scheduler: publishing user-uploaded video '{video_data['title']}'")
    outcome = await publish_video_locally(video_data)
    results = video_data.get("published_platforms", outcome.get("results", {}))
    _update_schedule_file(video_data)

    # Send email notification
    try:
        from notify.email_approver import send_approval_email
        await send_approval_email(
            creative_id=video_data.get("id", "scheduled"),
            title=f"PUBLISHED: {video_data['title']}",
            niche="User Upload",
            hook=video_data.get("hook", ""),
            caption=video_data.get("caption", ""),
            thumbnail_url="",
            video_url=video_data.get("video_path", ""),
            quality_score=100,
            predicted_views=0,
        )
        log.info("  Email notification sent")
    except Exception as e:
        log.warn(f"  Email notification failed: {e}")

    await _notify_chairman_published(video_data, results)
    return results


async def notify_generation_complete(creative_id, title, thumbnail_url, video_url, quality_score, prompt_dna):
    """When AI generates a video, send email for approval."""
    try:
        from notify.email_approver import send_approval_email
    except ImportError:
        try:
            from python_agents.notify.email_approver import send_approval_email
        except ImportError:
            log.warn("Scheduler: notify.email_approver module not available, skipping approval email.")
            return {"success": False, "error": "notify module not found"}

    log.info(f"Scheduler: AI video generated, sending approval email for '{title}'")

    try:
        result = await send_approval_email(
            creative_id=creative_id,
            title=title,
            niche="AI Generated",
            hook="",
            caption="",
            thumbnail_url=thumbnail_url,
            video_url=video_url,
            quality_score=quality_score,
            predicted_views=0,
        )
        return result
    except Exception as e:
        log.warn(f"Scheduler: approval email dispatch failed: {e}")
        return {"success": False, "error": str(e)}


def _update_schedule_file(updated_item):
    """Update schedule.json entry."""
    schedule_file = os.path.join(Config.OUTPUT_DIR, "schedule.json")
    if os.path.exists(schedule_file):
        with open(schedule_file, "r", encoding="utf-8") as f:
            schedules = json.load(f)
        for i, item in enumerate(schedules):
            if item.get("id") == updated_item.get("id"):
                schedules[i] = updated_item
                break
        with open(schedule_file, "w", encoding="utf-8") as f:
            json.dump(schedules, f, indent=2, ensure_ascii=False)


async def _notify_chairman_published(video_data, results):
    """Telegram notification when video published."""
    if not Config.TELEGRAM_BOT_TOKEN:
        return

    import httpx
    success_count = sum(1 for r in results.values() if r.get("status") == "success")

    message = (
        f"🚀 *VIDEO PUBLISHED!*\n\n"
        f"*Title:* {video_data['title']}\n"
        f"*Source:* User Upload (Scheduled)\n"
        f"*Date:* {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"*Platforms:* {success_count}/{len(results)} succeeded\n"
        f"*Keyword:* {video_data.get('comment_keyword', 'KIT')}"
    )

    url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": Config.TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, json=payload)
    except:
        pass


def add_to_schedule(
    video_path: str,
    title: str,
    hook: str = "",
    caption: str = "",
    hashtags: List[str] = None,
    scheduled_date: str = None,
    scheduled_time: str = "09:00",
    prompt_dna: str = "",
    comment_keyword: str = "KIT",
    prompt_to_send: str = "",
):
    """Add a video to the schedule."""
    Config.ensure_dirs()
    schedule_file = os.path.join(Config.OUTPUT_DIR, "schedule.json")

    if os.path.exists(schedule_file):
        with open(schedule_file, "r", encoding="utf-8") as f:
            schedules = json.load(f)
    else:
        schedules = []

    entry = {
        "id": f"vid_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "video_path": video_path,
        "title": title,
        "hook": hook,
        "caption": caption,
        "hashtags": hashtags or [],
        "scheduled_date": scheduled_date,
        "scheduled_time": scheduled_time,
        "status": "scheduled",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "prompt_dna": prompt_dna,
        "comment_keyword": comment_keyword,
        "prompt_to_send": prompt_to_send,
    }

    schedules.append(entry)

    with open(schedule_file, "w", encoding="utf-8") as f:
        json.dump(schedules, f, indent=2, ensure_ascii=False)

    log.info(f"Scheduler: video '{title}' added for {scheduled_date} at {scheduled_time}")
    return entry


def get_schedule() -> List[Dict]:
    """Get the full publish schedule."""
    schedule_file = os.path.join(Config.OUTPUT_DIR, "schedule.json")
    if os.path.exists(schedule_file):
        with open(schedule_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def remove_from_schedule(video_id: str):
    """Remove a video from the schedule."""
    schedule_file = os.path.join(Config.OUTPUT_DIR, "schedule.json")
    if os.path.exists(schedule_file):
        with open(schedule_file, "r", encoding="utf-8") as f:
            schedules = json.load(f)
        schedules = [s for s in schedules if s.get("id") != video_id]
        with open(schedule_file, "w", encoding="utf-8") as f:
            json.dump(schedules, f, indent=2, ensure_ascii=False)
