"""
UAAF Meta Publisher — Instagram & Facebook Reels via Meta Graph API v20.
Production-grade direct binary chunked rupload pipeline.

Requires:
  - META_ACCESS_TOKEN (System User or Long-Lived User Token)
  - META_IG_BUSINESS_ACCOUNT_ID (Instagram Business or Creator Account ID)
  - META_FB_PAGE_ID (Facebook Page ID)
"""
import os
import sys
import httpx
from typing import Dict, Optional

# Ensure project root in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from utils.logger import log

GRAPH_API_BASE = "https://graph.facebook.com/v20.0"


async def publish_instagram(video_path: str, caption: str, title: str = "") -> Dict:
    """
    Publish a Reel to Instagram via Meta Graph API using direct resumable binary upload.
    Delegates to the verified self-healing engine in publish_all.
    """
    from publish.publish_all import _publish_instagram
    return await _publish_instagram(video_source=video_path, caption=caption, title=title)


async def publish_facebook(video_path: str, caption: str, title: str = "") -> Dict:
    """
    Publish a Reel to Facebook Page via Meta Graph API using two-phase chunked upload.
    Delegates to the verified engine in publish_all.
    """
    from publish.publish_all import _publish_facebook
    return await _publish_facebook(video_source=video_path, caption=caption, title=title)


async def get_long_lived_token(short_lived_token: str) -> str:
    """
    Exchange a short-lived token for a long-lived (60-day) token.
    Call this once during setup to persist in .env.
    """
    url = f"{GRAPH_API_BASE}/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": Config.META_APP_ID,
        "client_secret": Config.META_APP_SECRET,
        "fb_exchange_token": short_lived_token,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()["access_token"]


async def verify_meta_credentials() -> Dict[str, any]:
    """
    Verify connectivity and permissions for configured Meta tokens.
    """
    token = Config.META_ACCESS_TOKEN
    ig_id = Config.META_IG_BUSINESS_ACCOUNT_ID
    page_id = Config.META_FB_PAGE_ID

    results = {
        "token_valid": False,
        "instagram": {"connected": False, "username": None, "id": ig_id},
        "facebook": {"connected": False, "page_name": None, "id": page_id},
    }

    if not token:
        return results

    async with httpx.AsyncClient(timeout=20) as client:
        # Check token debug info
        try:
            r = await client.get(f"{GRAPH_API_BASE}/me", params={"access_token": token})
            if r.status_code == 200:
                results["token_valid"] = True
        except Exception:
            pass

        # Check Instagram Account
        if ig_id:
            try:
                r_ig = await client.get(f"{GRAPH_API_BASE}/{ig_id}", params={"fields": "username,name", "access_token": token})
                if r_ig.status_code == 200:
                    data = r_ig.json()
                    results["instagram"]["connected"] = True
                    results["instagram"]["username"] = data.get("username")
            except Exception:
                pass

        # Check Facebook Page
        if page_id:
            try:
                r_fb = await client.get(f"{GRAPH_API_BASE}/{page_id}", params={"fields": "name", "access_token": token})
                if r_fb.status_code == 200:
                    data = r_fb.json()
                    results["facebook"]["connected"] = True
                    results["facebook"]["page_name"] = data.get("name")
            except Exception:
                pass

    return results
