"""
UAAF Unified Multi-Platform Video Publisher
===========================================
Publish a vertical short-form video clip to any or all supported social platforms:
YouTube Shorts, Instagram Reels, Facebook Reels, TikTok, and X (Twitter).

Usage:
    # 1. Validate video specifications and credentials without uploading:
    python -m examples.publish_clip examples/sample-vertical.mp4 --platform all --dry-run

    # 2. Publish to YouTube as Private (safe test):
    python -m examples.publish_clip examples/sample-vertical.mp4 --platform youtube --privacy private

    # 3. Publish to TikTok as Private (SELF_ONLY):
    python -m examples.publish_clip examples/sample-vertical.mp4 --platform tiktok --privacy private

    # 4. Publish to Instagram / Facebook / X (Requires explicit --allow-public or --privacy public):
    python -m examples.publish_clip examples/sample-vertical.mp4 --platform instagram --allow-public
    python -m examples.publish_clip examples/sample-vertical.mp4 --platform all --allow-public
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
PUBLIC_ONLY_PLATFORMS = {"instagram", "facebook", "x"}


def check_platform_credentials(platform: str) -> dict:
    """Check whether all required environment credentials exist for a platform."""
    if platform == "youtube":
        cid = bool(Config.YOUTUBE_CLIENT_ID)
        sec = bool(Config.YOUTUBE_CLIENT_SECRET)
        tok = bool(Config.YOUTUBE_REFRESH_TOKEN)
        return {
            "configured": cid and sec and tok,
            "details": f"CLIENT_ID={'SET' if cid else 'MISSING'}, CLIENT_SECRET={'SET' if sec else 'MISSING'}, REFRESH_TOKEN={'SET' if tok else 'MISSING'}",
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
        key = bool(Config.TIKTOK_CLIENT_KEY)
        sec = bool(Config.TIKTOK_CLIENT_SECRET)
        tok = bool(Config.TIKTOK_ACCESS_TOKEN or Config.TIKTOK_REFRESH_TOKEN)
        return {
            "configured": key and sec and tok,
            "details": f"CLIENT_KEY={'SET' if key else 'MISSING'}, CLIENT_SECRET={'SET' if sec else 'MISSING'}, TOKEN={'SET' if tok else 'MISSING'}",
            "setup_hint": "Run: python python_agents/utils/tiktok_auth.py",
        }
    elif platform == "x":
        key = bool(Config.X_API_KEY)
        sec = bool(Config.X_API_SECRET)
        tok = bool(Config.X_ACCESS_TOKEN)
        tok_sec = bool(Config.X_ACCESS_TOKEN_SECRET)
        return {
            "configured": key and sec and tok and tok_sec,
            "details": f"API_KEY={'SET' if key else 'MISSING'}, API_SECRET={'SET' if sec else 'MISSING'}, ACCESS_TOKEN={'SET' if tok else 'MISSING'}, ACCESS_SECRET={'SET' if tok_sec else 'MISSING'}",
            "setup_hint": "Add X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET to .env",
        }
    return {"configured": False, "details": "Unknown platform", "setup_hint": ""}


async def run_publisher(
    video_path: Path,
    target_platforms: list,
    title: str,
    caption: str,
    privacy: str,
    allow_public: bool = False,
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

    # 2. Privacy Constraints Check
    if "tiktok" in target_platforms and privacy == "unlisted":
        print("\n[ERROR] TikTok API v2 does not support 'unlisted' visibility.", file=sys.stderr)
        print("Supported TikTok visibility levels: 'private' (maps to SELF_ONLY) or 'public' (PUBLIC_TO_EVERYONE).", file=sys.stderr)
        sys.exit(1)

    # Guard: Public posting protection for Instagram, Facebook, and X
    skipped_for_privacy = []
    if privacy == "private" and not allow_public:
        unsupported = [p for p in target_platforms if p in PUBLIC_ONLY_PLATFORMS]
        if unsupported:
            if len(target_platforms) == len(unsupported):
                print(f"\n[ERROR] Platform(s) '{', '.join(unsupported)}' do not support private uploads.", file=sys.stderr)
                print("To publish publicly to these channels, pass --privacy public or --allow-public.", file=sys.stderr)
                sys.exit(1)
            else:
                skipped_for_privacy = unsupported
                target_platforms = [p for p in target_platforms if p not in PUBLIC_ONLY_PLATFORMS]

    # 3. Credential Check
    print(f"\n[2/3] Checking credentials for target platform(s): {', '.join(target_platforms)}")
    cred_status = {}
    missing_platforms = []
    for p in target_platforms:
        status = check_platform_credentials(p)
        cred_status[p] = status
        icon = "[CONFIGURED]" if status["configured"] else "[MISSING]"
        print(f"   {icon:<14} {p.upper():<10} - {status['details']}")
        if not status["configured"]:
            missing_platforms.append((p, status["setup_hint"]))

    if skipped_for_privacy:
        print("\n   Privacy Protection Notice:")
        for p in skipped_for_privacy:
            print(f"   [SKIPPED]      {p.upper():<10} - Platform only supports public posting. Pass --allow-public to publish.")

    if dry_run:
        print("\n[3/3] DRY RUN COMPLETED (No uploads performed)")
        print("=" * 65)
        print("Summary:")
        print(f" - Video specifications: PASS ({spec['width']}x{spec['height']}, {spec['duration_seconds']}s)")
        print(f" - Configured platforms: {[p for p in target_platforms if cred_status[p]['configured']]}")
        print(f" - Missing platforms:    {[p for p in target_platforms if not cred_status[p]['configured']]}")
        if skipped_for_privacy:
            print(f" - Skipped for privacy:  {skipped_for_privacy} (pass --allow-public to include)")
        if missing_platforms:
            print("\nSetup tips for missing credentials:")
            for p, hint in missing_platforms:
                print(f"   - {p.upper()}: {hint}")
        print("=" * 65)
        return

    # In live mode, verify at least one platform is configured
    configured_targets = [p for p in target_platforms if cred_status[p]["configured"]]
    if not configured_targets:
        print("\n[CONFIG ERROR] None of the selected platforms have complete credentials in .env.", file=sys.stderr)
        print("Please configure at least one platform before running a live publish:", file=sys.stderr)
        for p, hint in missing_platforms:
            print(f"   - {p.upper()}: {hint}", file=sys.stderr)
        sys.exit(1)

    # 4. Live Dispatch
    print(f"\n[3/3] Initiating live publication to: {', '.join(configured_targets)}...")
    start_time = time.time()

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
        if status in ("success", "uploaded_to_inbox"):
            url = res.get("url", res.get("media_id", "N/A"))
            tag = "INBOX" if status == "uploaded_to_inbox" else "SUCCESS"
            msg = f" ({res.get('message')})" if res.get("message") else ""
            print(f"   [{tag}] {p.upper():<10} -> {url}{msg}")
        elif status in ("pending", "timed_out"):
            all_succeeded = False
            msg = res.get("message", res.get("error", "Processing pending"))
            print(f"   [PENDING] {p.upper():<10} -> {msg}")
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
    parser.add_argument(
        "--allow-public",
        action="store_true",
        help="Explicitly permit public posting on platforms that do not support private mode (Instagram, Facebook, X)",
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
            allow_public=args.allow_public,
            dry_run=args.dry_run,
        )
    )


if __name__ == "__main__":
    main()
