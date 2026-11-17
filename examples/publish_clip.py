"""
UAAF Unified Multi-Platform Video Publisher
===========================================
Publish a vertical short-form video clip to any or all supported social platforms:
YouTube Shorts, Instagram Reels, Facebook Reels, TikTok, and X (Twitter).

Usage:
    # 1. Validate video specifications and credentials without uploading:
    python -m examples.publish_clip examples/sample-vertical.mp4 --platform all --dry-run

    # 2. Publish to a specific platform (e.g. YouTube as Private):
    python -m examples.publish_clip examples/sample-vertical.mp4 --platform youtube --privacy private

    # 3. Publish to Instagram Reels:
    python -m examples.publish_clip examples/sample-vertical.mp4 --platform instagram

    # 4. Publish to Facebook Reels:
    python -m examples.publish_clip examples/sample-vertical.mp4 --platform facebook

    # 5. Publish to TikTok (as Private / Self-Only):
    python -m examples.publish_clip examples/sample-vertical.mp4 --platform tiktok --privacy private

    # 6. Publish to X (Twitter):
    python -m examples.publish_clip examples/sample-vertical.mp4 --platform x

    # 7. Publish to ALL configured platforms simultaneously:
    python -m examples.publish_clip examples/sample-vertical.mp4 --platform all
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Add project root and python_agents to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python_agents"))
sys.path.insert(0, str(ROOT))

from config import Config
from publish.video_validation import short_form_check
from publish.publish_all import publish_to_all

ALL_PLATFORMS = ["youtube", "instagram", "facebook", "tiktok", "x"]


def check_platform_credentials(platform: str) -> dict:
    """Check whether required environment credentials exist for a platform."""
    if platform == "youtube":
        cid = bool(Config.YOUTUBE_CLIENT_ID)
        sec = bool(Config.YOUTUBE_CLIENT_SECRET)
        tok = bool(Config.YOUTUBE_REFRESH_TOKEN)
        return {
            "configured": cid and sec and tok,
            "details": f"CLIENT_ID={'SET' if cid else 'MISSING'}, REFRESH_TOKEN={'SET' if tok else 'MISSING'}",
            "setup_hint": "Run: python python_agents/utils/youtube_auth.py",
        }
    elif platform == "instagram":
        tok = bool(Config.META_ACCESS_TOKEN)
        ig = bool(Config.META_IG_BUSINESS_ACCOUNT_ID)
        return {
            "configured": tok and ig,
            "details": f"META_ACCESS_TOKEN={'SET' if tok else 'MISSING'}, IG_ACCOUNT_ID={'SET' if ig else 'MISSING'}",
            "setup_hint": "Add META_ACCESS_TOKEN and META_IG_BUSINESS_ACCOUNT_ID to .env",
        }
    elif platform == "facebook":
        tok = bool(Config.META_ACCESS_TOKEN)
        page = bool(Config.META_FB_PAGE_ID)
        return {
            "configured": tok and page,
            "details": f"META_ACCESS_TOKEN={'SET' if tok else 'MISSING'}, FB_PAGE_ID={'SET' if page else 'MISSING'}",
            "setup_hint": "Add META_ACCESS_TOKEN and META_FB_PAGE_ID to .env",
        }
    elif platform == "tiktok":
        tok = bool(Config.TIKTOK_ACCESS_TOKEN or Config.TIKTOK_REFRESH_TOKEN)
        key = bool(Config.TIKTOK_CLIENT_KEY)
        return {
            "configured": tok and key,
            "details": f"CLIENT_KEY={'SET' if key else 'MISSING'}, TOKEN={'SET' if tok else 'MISSING'}",
            "setup_hint": "Run: python python_agents/utils/tiktok_auth.py",
        }
    elif platform == "x":
        key = bool(Config.X_API_KEY)
        sec = bool(Config.X_API_SECRET)
        tok = bool(Config.X_ACCESS_TOKEN)
        tok_sec = bool(Config.X_ACCESS_TOKEN_SECRET)
        return {
            "configured": key and sec and tok and tok_sec,
            "details": f"API_KEY={'SET' if key else 'MISSING'}, ACCESS_TOKEN={'SET' if tok else 'MISSING'}",
            "setup_hint": "Add X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET to .env",
        }
    return {"configured": False, "details": "Unknown platform", "setup_hint": ""}


async def run_publisher(
    video_path: Path,
    target_platforms: list,
    title: str,
    caption: str,
    privacy: str,
    dry_run: bool = False,
):
    print("=" * 65)
    print("UAAF MULTI-PLATFORM SOCIAL PUBLISHER")
    print("=" * 65)

    # 1. Spec Validation
    print(f"\n[1/3] Validating video format: {video_path.name}")
    spec = short_form_check(str(video_path))
    is_vert = spec['height'] >= spec['width']
    print(f"   Dimensions: {spec['width']}x{spec['height']} (Vertical 9:16: {'YES' if is_vert else 'NO'})")
    print(f"   Duration:   {spec['duration_seconds']}s (Shorts/Reels limit: <= 180s)")
    print(f"   Eligible:   {spec['is_short_eligible']}")

    if not spec.get("is_short_eligible"):
        print("\n[ERROR] Video clip fails short-form specification checks.", file=sys.stderr)
        print("UAAF requires a 9:16 vertical video under 180 seconds duration.", file=sys.stderr)
        sys.exit(1)

    # 2. Credential Check
    print(f"\n[2/3] Checking credentials for target platform(s): {', '.join(target_platforms)}")
    cred_status = {}
    missing_platforms = []
    for p in target_platforms:
        status = check_platform_credentials(p)
        cred_status[p] = status
        icon = "[READY]" if status["configured"] else "[MISSING]"
        print(f"   {icon} {p.upper():<10} - {status['details']}")
        if not status["configured"]:
            missing_platforms.append((p, status["setup_hint"]))

    if dry_run:
        print("\n[3/3] DRY RUN COMPLETED (No uploads performed)")
        print("=" * 65)
        print("Summary:")
        print(f" - Video specifications: PASS ({spec['width']}x{spec['height']}, {spec['duration_seconds']}s)")
        print(f" - Configured platforms: {[p for p in target_platforms if cred_status[p]['configured']]}")
        print(f" - Missing platforms:    {[p for p in target_platforms if not cred_status[p]['configured']]}")
        if missing_platforms:
            print("\nSetup tips for missing credentials:")
            for p, hint in missing_platforms:
                print(f"   - {p.upper()}: {hint}")
        print("=" * 65)
        return

    # In live mode, verify at least one platform is configured
    configured_targets = [p for p in target_platforms if cred_status[p]["configured"]]
    if not configured_targets:
        print("\n[CONFIG ERROR] None of the selected platforms have credentials in .env.", file=sys.stderr)
        print("Please configure at least one platform before running a live publish:", file=sys.stderr)
        for p, hint in missing_platforms:
            print(f"   - {p.upper()}: {hint}", file=sys.stderr)
        sys.exit(1)

    # 3. Live Dispatch
    print(f"\n[3/3] Initiating live publication to: {', '.join(configured_targets)}...")
    start_time = time.time()

    # Map privacy level for specific platform requirements
    tiktok_priv = "SELF_ONLY" if privacy == "private" else "PUBLIC_TO_EVERYONE"

    results = await publish_to_all(
        video_path=str(video_path),
        caption=caption,
        title=title,
        hashtags=["#uaaf", "#shorts", "#reels"],
        platforms=configured_targets,
        youtube_privacy=privacy,
        tiktok_privacy=tiktok_priv,
        privacy=privacy,
    )

    elapsed = time.time() - start_time
    print("\n" + "=" * 65)
    print(f"PUBLICATION RESULTS ({elapsed:.1f}s)")
    print("=" * 65)

    all_succeeded = True
    for p in configured_targets:
        res = results.get(p, {})
        status = res.get("status")
        if status == "success":
            url = res.get("url", res.get("media_id", "N/A"))
            print(f"   [SUCCESS] {p.upper():<10} -> {url}")
        else:
            all_succeeded = False
            err = res.get("error", "Unknown error")
            print(f"   [FAILED]  {p.upper():<10} -> {err}")

    print("=" * 65)
    if not all_succeeded:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="UAAF Multi-Platform Video Publisher CLI.")
    parser.add_argument("video", nargs="?", default="examples/sample-vertical.mp4", help="Path to vertical MP4 clip")
    parser.add_argument(
        "--platform",
        default="all",
        choices=["youtube", "instagram", "facebook", "tiktok", "x", "all"],
        help="Target platform (default: all)",
    )
    parser.add_argument("--title", default="UAAF Clip", help="Title for YouTube / Facebook")
    parser.add_argument("--caption", default="Published via UAAF Social Publisher", help="Post caption")
    parser.add_argument(
        "--privacy",
        default="private",
        choices=["private", "unlisted", "public"],
        help="Privacy visibility status (default: private for safe testing)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate video specs and credentials without uploading")

    args = parser.parse_args()
    video_path = Path(args.video).resolve()

    if not video_path.exists():
        print(f"[ERROR] Video file not found: {video_path}", file=sys.stderr)
        sys.exit(1)

    targets = ALL_PLATFORMS if args.platform == "all" else [args.platform]
    asyncio.run(
        run_publisher(
            video_path=video_path,
            target_platforms=targets,
            title=args.title,
            caption=args.caption,
            privacy=args.privacy,
            dry_run=args.dry_run,
        )
    )


if __name__ == "__main__":
    main()
