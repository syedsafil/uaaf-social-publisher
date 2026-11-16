"""Secure Meta comment webhook for the per-video comment-to-unlock flow.

Meta provides comment events for Instagram/Facebook. Other platforms need their
own approved APIs and must never be presented as automatically monitored here.
"""
import hashlib
import hmac
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse
import uvicorn

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from utils.logger import log
from webhook.dm_dispatcher import handle_lemonsqueezy_webhook, trigger_dm_funnel

app = FastAPI(title="UAAF Comment Webhook", version="2.0.0", docs_url="/docs", redoc_url=None)


def _schedule_file() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "schedule.json")


def find_video_by_keyword(comment: str, post_id: str) -> Optional[Dict[str, Any]]:
    """Only return a keyword match for the post that was actually published."""
    try:
        with open(_schedule_file(), "r", encoding="utf-8") as source:
            videos = json.load(source)
    except (OSError, json.JSONDecodeError):
        return None

    comment_upper = comment.upper().strip()
    for video in videos:
        post_ids = {str(item.get("media_id", "")) for item in video.get("published_platforms", {}).values()}
        keyword = video.get("comment_keyword", "").upper().strip()
        if keyword and keyword in comment_upper and (not post_id or post_id in post_ids):
            return video
    return None


def valid_signature(body: bytes, signature: str) -> bool:
    """Reject forged webhook requests when META_APP_SECRET is configured."""
    if not Config.META_APP_SECRET:
        return True
    expected = "sha256=" + hmac.new(Config.META_APP_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")


@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    if hub_mode == "subscribe" and hmac.compare_digest(hub_verify_token or "", Config.META_WEBHOOK_VERIFY_TOKEN):
        return PlainTextResponse(hub_challenge or "")
    raise HTTPException(status_code=403, detail="Webhook verification token mismatch")


@app.post("/webhook")
async def receive_meta_webhook(request: Request):
    raw = await request.body()
    if not valid_signature(raw, request.headers.get("x-hub-signature-256", "")):
        raise HTTPException(status_code=403, detail="Invalid webhook signature")
    try:
        body = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    platform = body.get("object", "")
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") != "comments":
                continue
            value = change.get("value", {})
            await handle_comment(value, platform)
    return JSONResponse({"status": "received"})


async def handle_comment(value: Dict[str, Any], platform: str):
    comment = value.get("text", "")
    user = value.get("from", {})
    user_id = user.get("id", "")
    post_id = value.get("media", {}).get("id", "")
    if not comment or not user_id:
        return

    video = find_video_by_keyword(comment, post_id)
    if not video:
        return
    log.info(f"Comment unlock: {platform} post={post_id}, video={video.get('id')}")
    try:
        await trigger_dm_funnel(
            platform=platform,
            user_id=user_id,
            user_name=user.get("name", "there"),
            post_id=post_id,
            comment_id=value.get("id", ""),
            prompt_dna=video.get("prompt_to_send", ""),
        )
    except Exception as error:
        # Return 200 to Meta; retries of a business-rule failure create duplicate DMs.
        log.error(f"Comment unlock failed: {error}")


@app.post("/webhook/lemonsqueezy")
async def receive_lemonsqueezy_webhook(request: Request):
    event = await request.json()
    return JSONResponse(await handle_lemonsqueezy_webhook(event))


@app.get("/health")
async def health():
    return {"status": "ok", "service": "comment-webhook", "time": datetime.now(timezone.utc).isoformat()}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=Config.WEBHOOK_PORT)
