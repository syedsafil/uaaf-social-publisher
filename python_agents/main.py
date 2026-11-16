"""
UAAF MAIN ORCHESTRATOR — 24/7 AUTONOMOUS CYCLE (FIXED)
═══════════════════════════════════════════════════════════════
FIXES:
1. datetime.utcnow() → datetime.now(timezone.utc)
2. argparse CLI for manual publish mode
3. Schedule sync fixed (local timezone aware)
═══════════════════════════════════════════════════════════════
"""
import asyncio
import json
import os
import sys
import argparse
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from utils.logger import log
from scheduler import check_today_schedule, publish_scheduled_video, notify_generation_complete
from research.research_agent import research_trend
from render.tts_engine import generate_voiceover
from render.asset_fetcher import fetch_scene_videos
from render.video_compiler import VideoCompiler


async def run_autonomous_cycle(niche="auto"):
    """
    The complete 24/7 cycle.
    Checks schedule first → publishes user upload OR generates new.
    """
    start_time = datetime.now(timezone.utc)
    log.info("=" * 60)
    log.info("UAAF AUTONOMOUS CYCLE STARTED")
    log.info(f"  Time: {start_time.isoformat()}")
    log.info(f"  Auto-publish: {Config.ENABLE_AUTO_PUBLISH}")
    log.info("=" * 60)

    Config.validate()
    Config.ensure_dirs()

    try:
        # ══ STEP 1: CHECK SCHEDULE ══
        log.info("\n📅 STEP 1: Checking publish schedule...")
        schedule_result = await check_today_schedule()

        if schedule_result["mode"] == "user_upload":
            # ══ USER UPLOADED VIDEO — PUBLISH DIRECTLY ══
            video_data = schedule_result["video"]
            log.info(f"\n🚀 Publishing user-uploaded video: {video_data['title']}")

            results = await publish_scheduled_video(video_data)
            log.info(f"Published to {sum(1 for r in results.values() if r.get('status') == 'success')}/{len(results)} platforms")

            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            log.info(f"\n✅ Cycle complete in {elapsed:.0f}s (user upload mode)")
            return {"status": "success", "mode": "user_upload", "results": results}

        # ══ NO USER UPLOAD — GENERATE NEW VIDEO ══
        log.info("\n🤖 No user upload — generating new video...")

        # STEP 2: Research + Script
        log.info("\n📋 STEP 2: Research Agent generating concept...")
        concept = await research_trend(niche)
        log.info(f"   Title: {concept['title']}")
        log.info(f"   Hook: {concept['hook']}")

        # STEP 3: Generate Voiceover
        log.info("\n🎤 STEP 3: TTS Engine generating voiceover...")
        voiceover_text = concept.get("voiceover_full", concept.get("caption", ""))
        voiceover_path = await generate_voiceover(
            text=voiceover_text,
            rate="-10%",
        )
        log.info(f"   Voiceover: {voiceover_path}")

        # STEP 4: Fetch Video Assets (PEXELS)
        log.info("\n🎬 STEP 4: Fetching REAL video footage from Pexels...")
        scene_assets = await fetch_scene_videos(concept.get("scenes", []))
        log.info(f"   {len(scene_assets)} video clips fetched")

        if not scene_assets:
            raise RuntimeError("No video assets fetched — cannot compile")

        # STEP 5: Compile Video
        log.info("\n🎞️ STEP 5: Compiling final video (FFmpeg)...")
        compiler = VideoCompiler()
        video_path = compiler.compile(
            script=concept,
            scene_assets=scene_assets,
            voiceover_path=voiceover_path,
            background_music_path=None,
            comment_keyword=Config.DM_TRIGGER_KEYWORD,
        )
        log.info(f"   Final video: {video_path}")

        # STEP 6: Save entry & Send Approval Email
        log.info("\n📧 STEP 6: Registering creative & sending approval email...")
        creative_id = f"creative_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        # Save to output/schedule.json
        schedule_file = os.path.join(Config.OUTPUT_DIR, "schedule.json")
        if os.path.exists(schedule_file):
            try:
                with open(schedule_file, "r", encoding="utf-8") as f:
                    schedules = json.load(f)
            except Exception:
                schedules = []
        else:
            schedules = []

        entry = {
            "id": creative_id,
            "video_path": video_path,
            "title": concept.get("title", "Untitled"),
            "hook": concept.get("hook", ""),
            "caption": concept.get("caption", ""),
            "hashtags": concept.get("hashtags", []),
            "scheduled_date": datetime.now().strftime("%Y-%m-%d"),
            "scheduled_time": datetime.now().strftime("%H:%M"),
            "status": "pending_approval",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "prompt_dna": concept.get("prompt_dna", ""),
            "comment_keyword": getattr(Config, "DM_TRIGGER_KEYWORD", "KIT"),
            "prompt_to_send": getattr(Config, "LEMON_SQUEEZY_CHECKOUT_URL", "https://lemonsqueezy.com"),
        }
        schedules.append(entry)
        with open(schedule_file, "w", encoding="utf-8") as f:
            json.dump(schedules, f, indent=2, ensure_ascii=False)

        try:
            await notify_generation_complete(
                creative_id=creative_id,
                title=concept["title"],
                thumbnail_url="",
                video_url=video_path,
                quality_score=concept.get("quality_prediction", {}).get("luxury_score", 0),
                prompt_dna=concept.get("prompt_dna", ""),
            )
            log.info("   Approval email sent — waiting for Chairman approval")
        except Exception as e:
            log.warn(f"   Email failed: {e} — video queued in output folder")

        # If auto-publish is ON
        if Config.ENABLE_AUTO_PUBLISH:
            log.info("\n🚀 Auto-publish enabled — publishing now...")
            from publish.publish_all import publish_to_all
            results = await publish_to_all(
                video_path=video_path,
                caption=concept.get("caption", ""),
                title=concept["title"],
                hashtags=concept.get("hashtags", []),
            )
            log.info(f"Published: {sum(1 for r in results.values() if r.get('status') == 'success')}/{len(results)}")
        else:
            log.info("\n⏸️  Auto-publish OFF — Chairman must approve via email or dashboard")

        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        log.info("\n" + "=" * 60)
        log.info("UAAF AUTONOMOUS CYCLE COMPLETE")
        log.info(f"  Total time: {elapsed:.0f}s")
        log.info("=" * 60)

        await _notify_chairman(concept, video_path, elapsed)

        return {
            "status": "success",
            "mode": "auto_generate",
            "concept": concept,
            "video": video_path,
        }

    except Exception as e:
        log.error(f"CYCLE FAILED: {e}")
        import traceback
        log.error(traceback.format_exc())
        return {"status": "failed", "error": str(e)}


async def publish_manual_video(video_path, caption="", title="", hashtags=None):
    """
    Manually publish a specific video file to all platforms.
    CLI: python main.py publish --video path/to/video.mp4 --caption "..." --title "..."
    """
    log.info("=" * 60)
    log.info("MANUAL PUBLISH MODE")
    log.info(f"  Video: {video_path}")
    log.info(f"  Title: {title}")
    log.info(f"  Caption: {caption}")
    log.info("=" * 60)

    if not os.path.exists(video_path):
        log.error(f"Video file not found: {video_path}")
        return {"status": "failed", "error": "File not found"}

    Config.validate()

    try:
        from publish.publish_all import publish_to_all
        results = await publish_to_all(
            video_path=video_path,
            caption=caption,
            title=title or os.path.basename(video_path),
            hashtags=hashtags or [],
        )
        log.info(f"Published: {sum(1 for r in results.values() if r.get('status') == 'success')}/{len(results)}")
        return {"status": "success", "results": results}
    except Exception as e:
        log.error(f"Publish failed: {e}")
        return {"status": "failed", "error": str(e)}


async def _notify_chairman(concept, video_path, elapsed):
    """Send Telegram notification."""
    if not Config.TELEGRAM_BOT_TOKEN:
        return

    import httpx
    message = (
        f"🎬 *UAAF Daily Cycle Complete*\n\n"
        f"*Title:* {concept['title']}\n"
        f"*Niche:* {concept.get('niche', 'N/A')}\n"
        f"*Hook:* \"{concept['hook']}\"\n"
        f"*Duration:* {elapsed:.0f}s\n"
        f"*Status:* {'Published' if Config.ENABLE_AUTO_PUBLISH else 'Awaiting approval'}"
    )

    url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": Config.TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}

    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload)
    except:
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UAAF Autonomous Cycle")
    parser.add_argument("mode", nargs="?", default="auto", help="Mode: auto (generate) or publish (manual)")
    parser.add_argument("--video", type=str, help="Path to video file (for publish mode)")
    parser.add_argument("--caption", type=str, default="", help="Caption for manual publish")
    parser.add_argument("--title", type=str, default="", help="Title for manual publish")
    parser.add_argument("--hashtags", type=str, default="", help="Hashtags (space-separated)")
    parser.add_argument("niche", nargs="?", default="auto", help="Niche for auto mode")

    args = parser.parse_args()

    if args.mode == "publish":
        if not args.video:
            print("Error: --video path required for publish mode")
            sys.exit(1)
        tags = args.hashtags.split() if args.hashtags else []
        result = asyncio.run(publish_manual_video(
            video_path=args.video,
            caption=args.caption,
            title=args.title,
            hashtags=tags,
        ))
    else:
        result = asyncio.run(run_autonomous_cycle(args.niche))

    print(json.dumps(result, indent=2, default=str))
