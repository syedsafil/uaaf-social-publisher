"""
UAAF YouTube Short Publisher Example
====================================
Uploads a local vertical MP4 clip as a YouTube Short using the YouTube Data API v3.

Usage:
    python -m examples.publish_youtube_short examples/sample-vertical.mp4
    python -m examples.publish_youtube_short examples/sample-vertical.mp4 --privacy private
    python -m examples.publish_youtube_short examples/sample-vertical.mp4 --dry-run
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.parse
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from python_agents.publish.video_validation import short_form_check


def get_env_var(name: str) -> str:
    """Read variable from environment or .env file."""
    val = os.getenv(name)
    if val:
        return val.strip("\"' ")
    env_file = ROOT / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{name}="):
                    return line.split("=", 1)[1].strip("\"' ")
    return ""


def refresh_access_token(client_id: str, client_secret: str, refresh_token: str) -> str:
    """Exchange refresh token for a short-lived access token."""
    url = "https://oauth2.googleapis.com/token"
    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }).encode("utf-8")

    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read().decode("utf-8"))
        return body["access_token"]


def publish_short(video_path: Path, title: str, privacy: str, dry_run: bool = False):
    print(f"\n1. Validating clip specifications: {video_path.name}")
    spec = short_form_check(str(video_path))
    print(f"   - Dimensions: {spec['width']}x{spec['height']}")
    print(f"   - Duration:   {spec['duration_seconds']}s")
    print(f"   - Eligible:   {spec['is_short_eligible']}")

    if not spec.get("is_short_eligible"):
        print("\n[ERROR] Video is not vertical or exceeds duration limit for Shorts.", file=sys.stderr)
        sys.exit(1)

    client_id = get_env_var("YOUTUBE_CLIENT_ID")
    client_secret = get_env_var("YOUTUBE_CLIENT_SECRET")
    refresh_token = get_env_var("YOUTUBE_REFRESH_TOKEN")

    if dry_run:
        print("\n[DRY RUN] Local verification passed. Environment check:")
        print(f"   - YOUTUBE_CLIENT_ID:     {'[SET]' if client_id else '[NOT SET]'}")
        print(f"   - YOUTUBE_CLIENT_SECRET: {'[SET]' if client_secret else '[NOT SET]'}")
        print(f"   - YOUTUBE_REFRESH_TOKEN: {'[SET]' if refresh_token else '[NOT SET]'}")
        print("\nDry run completed. Video specifications conform to YouTube Shorts standard.")
        return

    if not (client_id and client_secret and refresh_token):
        print("\n[CONFIG REQUIRED] Missing YouTube API credentials.", file=sys.stderr)
        print("1. Copy .env.example to .env and set YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET", file=sys.stderr)
        print("2. Run token generator: python python_agents/utils/youtube_auth.py", file=sys.stderr)
        print("3. Alternatively, test locally with: python -m examples.publish_youtube_short examples/sample-vertical.mp4 --dry-run", file=sys.stderr)
        sys.exit(1)

    print("\n2. Authenticating with YouTube Data API v3...")
    try:
        access_token = refresh_access_token(client_id, client_secret, refresh_token)
        print("   - OAuth 2.0 access token successfully refreshed.")
    except Exception as e:
        print(f"\n[AUTH ERROR] Could not refresh OAuth token: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"\n3. Initiating upload session (privacy: {privacy})...")
    file_size = video_path.stat().st_size

    upload_endpoint = (
        "https://www.googleapis.com/upload/youtube/v3/videos"
        "?uploadType=resumable&part=snippet,status"
    )
    metadata = {
        "snippet": {
            "title": title[:100],
            "description": f"{title}\n\nUploaded via UAAF Social Publisher\n#shorts",
            "categoryId": "22",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }
    meta_bytes = json.dumps(metadata).encode("utf-8")

    init_req = urllib.request.Request(
        upload_endpoint,
        data=meta_bytes,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": "video/mp4",
            "X-Upload-Content-Length": str(file_size),
        },
        method="POST",
    )

    with urllib.request.urlopen(init_req) as init_resp:
        session_url = init_resp.headers.get("Location")

    if not session_url:
        print("[ERROR] Failed to obtain resumable upload session URL.", file=sys.stderr)
        sys.exit(1)

    print(f"4. Uploading video data ({file_size / 1024:.1f} KB)...")
    with open(video_path, "rb") as f:
        video_bytes = f.read()

    upload_req = urllib.request.Request(
        session_url,
        data=video_bytes,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "video/mp4",
            "Content-Length": str(file_size),
        },
        method="PUT",
    )

    with urllib.request.urlopen(upload_req) as upload_resp:
        res_body = json.loads(upload_resp.read().decode("utf-8"))
        video_id = res_body.get("id")
        short_url = f"https://www.youtube.com/shorts/{video_id}"

    result = {
        "status": "success",
        "platform": "youtube",
        "video_id": video_id,
        "url": short_url,
        "privacy": privacy,
        "is_short": True,
    }

    print("\n" + "=" * 50)
    print("PUBLICATION COMPLETED")
    print("=" * 50)
    print(json.dumps(result, indent=2))
    print(f"\nLive Short URL: {short_url}\n")


def main():
    parser = argparse.ArgumentParser(description="Publish a local vertical video to YouTube Shorts.")
    parser.add_argument("video", nargs="?", default="examples/sample-vertical.mp4", help="Path to vertical MP4 clip")
    parser.add_argument("--title", default="UAAF Test Short", help="Video title")
    parser.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"], help="Visibility status")
    parser.add_argument("--dry-run", action="store_true", help="Validate video specs and config without uploading")

    args = parser.parse_args()
    video_path = Path(args.video).resolve()
    if not video_path.exists():
        print(f"[ERROR] Video file not found: {video_path}", file=sys.stderr)
        sys.exit(1)

    publish_short(video_path, args.title, args.privacy, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
