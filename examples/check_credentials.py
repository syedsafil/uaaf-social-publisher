"""
UAAF Social Platforms Credentials Auditor
=========================================
Checks offline syntax and optional online authentication across all 5 platforms.

Usage:
    # 1. Offline environment audit:
    python -m examples.check_credentials

    # 2. Online API connectivity check:
    python -m examples.check_credentials --online
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root and python_agents to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python_agents"))
sys.path.insert(0, str(ROOT))

import httpx
from config import Config
from examples.publish_clip import check_platform_credentials, ALL_PLATFORMS
from publish.meta_publisher import verify_meta_credentials


async def audit_online():
    print("\n" + "=" * 65)
    print("ONLINE API CONNECTIVITY VERIFICATION")
    print("=" * 65)

    # 1. Meta (Instagram & Facebook)
    print("\n[Meta Graph API v20]")
    if Config.META_ACCESS_TOKEN:
        meta_res = await verify_meta_credentials()
        print(f"  Token Valid:      {'YES' if meta_res['token_valid'] else 'NO / EXPIRED'}")
        print(f"  Instagram Reel:   {'CONNECTED (@' + str(meta_res['instagram']['username']) + ')' if meta_res['instagram']['connected'] else 'NOT CONNECTED'}")
        print(f"  Facebook Page:    {'CONNECTED (' + str(meta_res['facebook']['page_name']) + ')' if meta_res['facebook']['connected'] else 'NOT CONNECTED'}")
    else:
        print("  Skipped: META_ACCESS_TOKEN not configured in .env")

    # 2. YouTube
    print("\n[YouTube Data API v3]")
    if Config.YOUTUBE_CLIENT_ID and Config.YOUTUBE_REFRESH_TOKEN:
        try:
            token_url = "https://oauth2.googleapis.com/token"
            data = {
                "client_id": Config.YOUTUBE_CLIENT_ID,
                "client_secret": Config.YOUTUBE_CLIENT_SECRET,
                "refresh_token": Config.YOUTUBE_REFRESH_TOKEN,
                "grant_type": "refresh_token",
            }
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(token_url, data=data)
                if r.status_code == 200:
                    print("  OAuth Token:      VALID (Access token successfully acquired)")
                else:
                    print(f"  OAuth Token:      FAILED (HTTP {r.status_code}: {r.json().get('error_description', r.text)})")
        except Exception as e:
            print(f"  OAuth Error:      {e}")
    else:
        print("  Skipped: YouTube credentials not configured in .env")

    # 3. TikTok
    print("\n[TikTok Content Posting API v2]")
    tok = Config.TIKTOK_ACCESS_TOKEN
    if tok:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(
                    "https://open.tiktokapis.com/v2/user/info/?fields=open_id,display_name",
                    headers={"Authorization": f"Bearer {tok}"}
                )
                if r.status_code == 200:
                    data = r.json().get("data", {}).get("user", {})
                    name = data.get("display_name", "Authorized Creator")
                    print(f"  TikTok Account:   CONNECTED ({name})")
                else:
                    print(f"  TikTok Token:     EXPIRED or INVALID (HTTP {r.status_code})")
        except Exception as e:
            print(f"  TikTok Error:     {e}")
    else:
        print("  Skipped: TIKTOK_ACCESS_TOKEN not configured in .env")

    # 4. X.com
    print("\n[X.com / Twitter Media Upload API v2]")
    if Config.X_API_KEY and Config.X_ACCESS_TOKEN:
        try:
            import tweepy
            client = tweepy.Client(
                bearer_token=Config.X_BEARER_TOKEN or None,
                consumer_key=Config.X_API_KEY,
                consumer_secret=Config.X_API_SECRET,
                access_token=Config.X_ACCESS_TOKEN,
                access_token_secret=Config.X_ACCESS_TOKEN_SECRET,
            )
            me = client.get_me()
            if me and me.data:
                print(f"  X.com Account:    CONNECTED (@{me.data.username})")
            else:
                print("  X.com Account:    CONNECTED (Credentials accepted)")
        except Exception as e:
            print(f"  X.com Status:     FAILED ({e})")
    else:
        print("  Skipped: X.com credentials not configured in .env")

    print("\n" + "=" * 65)


def main():
    parser = argparse.ArgumentParser(description="UAAF Social Platforms Credentials Auditor.")
    parser.add_argument("--online", action="store_true", help="Perform live online API connectivity verification")
    args = parser.parse_args()

    print("=" * 65)
    print("UAAF SOCIAL PLATFORMS CREDENTIALS AUDIT (OFFLINE)")
    print("=" * 65)

    ready_count = 0
    for p in ALL_PLATFORMS:
        res = check_platform_credentials(p)
        status = "[CONFIGURED]" if res["configured"] else "[NOT SET]"
        if res["configured"]:
            ready_count += 1
        print(f"\n* {p.upper()}: {status}")
        print(f"  Details: {res['details']}")
        if not res["configured"]:
            print(f"  Setup:   {res['setup_hint']}")

    print("\n" + "=" * 65)
    print(f"Audit Summary: {ready_count}/{len(ALL_PLATFORMS)} platforms configured.")
    if ready_count == 0:
        print("Tip: Copy .env.example to .env and configure your desired channels.")
    else:
        print("Tip: Run with --online to test live API connectivity with configured channels.")
    print("=" * 65)

    if args.online:
        asyncio.run(audit_online())


if __name__ == "__main__":
    main()
