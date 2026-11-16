import asyncio
import os
import random
import sys
import time
import json
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from utils.logger import log

REPLIED_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "replied_comments.json")
REPLIED_COMMENTS = set()

def load_replied_ids():
    global REPLIED_COMMENTS
    if os.path.exists(REPLIED_FILE):
        try:
            with open(REPLIED_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    REPLIED_COMMENTS.update(str(x) for x in data)
        except Exception:
            pass

def save_replied_id(c_id: str):
    global REPLIED_COMMENTS
    if not c_id:
        return
    REPLIED_COMMENTS.add(str(c_id))
    try:
        os.makedirs(os.path.dirname(REPLIED_FILE), exist_ok=True)
        with open(REPLIED_FILE, "w", encoding="utf-8") as f:
            json.dump(list(REPLIED_COMMENTS), f)
    except Exception:
        pass

load_replied_ids()
SCHEDULE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "schedule.json")
FOLLOW_STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "follow_state.json")
FOLLOW_STATE = {"reminded": set(), "verified": set()}

def load_follow_state():
    global FOLLOW_STATE
    if os.path.exists(FOLLOW_STATE_FILE):
        try:
            with open(FOLLOW_STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                FOLLOW_STATE["reminded"] = set(data.get("reminded", []))
                FOLLOW_STATE["verified"] = set(data.get("verified", []))
        except Exception:
            pass

def save_follow_state():
    try:
        os.makedirs(os.path.dirname(FOLLOW_STATE_FILE), exist_ok=True)
        with open(FOLLOW_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "reminded": list(FOLLOW_STATE["reminded"]),
                "verified": list(FOLLOW_STATE["verified"]),
            }, f, indent=2)
    except Exception:
        pass

load_follow_state()

def is_verified_follower(user_key: str) -> bool:
    return user_key.lower().strip() in FOLLOW_STATE["verified"]

def has_been_reminded(user_key: str) -> bool:
    return user_key.lower().strip() in FOLLOW_STATE["reminded"]

def mark_reminded(user_key: str):
    FOLLOW_STATE["reminded"].add(user_key.lower().strip())
    save_follow_state()

def mark_verified(user_key: str):
    FOLLOW_STATE["verified"].add(user_key.lower().strip())
    save_follow_state()


def load_schedule_items():
    """Extract all active schedule items from schedule.json"""
    if os.path.exists(SCHEDULE_FILE):
        try:
            with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    return []


def encode_prompt_payload(text: str) -> str:
    if not text:
        return ""
    try:
        import base64
        return base64.urlsafe_b64encode(text.strip().encode('utf-8')).decode('ascii').rstrip('=')
    except Exception:
        return ""

def detect_keyword(text: str, caption: str = "", media_id: str = "") -> tuple:
    """Dynamically match comment to its exact scheduled video keyword, video_id, prompt_to_send, and title."""
    t = text.upper().strip()
    c = caption.upper().strip()
    clean_t = "".join(ch for ch in t if ch.isalnum())

    items = load_schedule_items()

    # 1. Match by media_id in published_platforms
    if media_id:
        for item in items:
            pub = item.get("published_platforms") or {}
            for p in pub.values():
                if isinstance(p, dict):
                    if (
                        p.get("media_id") == media_id
                        or p.get("id") == media_id
                        or (p.get("url") and media_id in str(p.get("url")))
                    ):
                        kw = (item.get("comment_keyword") or "PROMPT").strip().upper()
                        vid = item.get("id") or media_id
                        prompt = item.get("prompt_to_send") or item.get("caption") or ""
                        title = item.get("title") or ""
                        return kw, vid, prompt, title

    # 2. Match by caption / title similarity
    if c:
        for item in items:
            title = item.get("title") or ""
            upper_title = title.upper()
            item_cap = (item.get("caption") or "").upper()
            kw = (item.get("comment_keyword") or "").upper().strip()
            prompt = item.get("prompt_to_send") or item.get("caption") or ""

            title_match = bool(upper_title and (upper_title[:15] in c or c in upper_title))
            cap_match = bool(item_cap and (item_cap[:25] in c or c[:25] in item_cap))
            kw_in_cap = bool(kw and kw in c)

            if title_match or cap_match or kw_in_cap:
                if kw:
                    return kw, item.get("id") or "", prompt, title

    # 3. Match by comment keyword directly
    for item in items:
        kw = (item.get("comment_keyword") or "").upper().strip()
        clean_kw = "".join(ch for ch in kw if ch.isalnum())
        prompt = item.get("prompt_to_send") or item.get("caption") or ""
        title = item.get("title") or ""
        if kw and (kw in t or (clean_kw and clean_kw in clean_t)):
            return kw, item.get("id") or "", prompt, title

    return "", "", "", ""


def get_follow_reminder_comment(author: str, platform: str = "instagram") -> str:
    clean_user = f"@{author.lstrip('@')}" if author else "there"
    target_handle = "@visionvaultsai" if platform == "instagram" else "our page"
    openers = [
        f"Hey {clean_user}!",
        f"Great to see you {clean_user}!",
        f"Awesome {clean_user}!",
        f"Good choice {clean_user}!",
        f"Hi {clean_user}!",
        f"Hello {clean_user}!",
        f"Love the interest {clean_user}!",
        f"Glad you're here {clean_user}!",
    ]
    rules = [
        f"Please make sure to follow {target_handle} first, otherwise our DM won't go through!",
        f"Quick note: please hit follow first, or direct messages cannot be delivered!",
        f"Please follow {target_handle} first, otherwise the automated DM won't work!",
        f"Make sure you're following us first so the system can deliver your DM!",
        f"Kindly follow {target_handle} first, otherwise DMs are blocked by the platform!",
        f"Be sure to follow first, otherwise the DM won't reach your inbox!",
        f"Make sure you follow first so {'Instagram' if platform == 'instagram' else 'Facebook'} allows the DM delivery!",
    ]
    next_steps = [
        "Drop another comment right after following to get your prompt! 🔒✨",
        "Leave a comment once followed and we'll send it immediately! 📩",
        "Reply here once followed to receive your prompt! 🚀",
        "Comment again right after to get your link! 💡",
        "Drop a quick comment once done and your DM will arrive! 🎯",
        "Drop another comment once you follow! 💫",
    ]
    return f"{random.choice(openers)} {random.choice(rules)} {random.choice(next_steps)}"


def get_dm_confirmation_comment(author: str, platform: str = "instagram", keyword: str = "") -> str:
    """
    Modular Combinatorial Comment Reply Engine:
    20 Openers x 20 Action Phrases x 12 Closers = 4,800+ unique, natural, anti-ban reply variations.
    No "Requests tab" mentions — direct, clean, human-like.
    """
    clean_user = f"@{author.lstrip('@').strip()}" if author else ""
    kw = keyword.upper().strip() if keyword else ""

    openers_with_user = [
        f"Done {clean_user}!",
        f"All set {clean_user}!",
        f"Sent your way {clean_user}!",
        f"Delivered {clean_user}!",
        f"Awesome {clean_user}!",
        f"Good choice {clean_user}!",
        f"On its way {clean_user}!",
        f"Just sent it over {clean_user}!",
        f"Prompt dispatched {clean_user}!",
        f"Ready for you {clean_user}!",
        f"Check your inbox {clean_user}!",
        f"You got it {clean_user}!",
        f"Here you go {clean_user}!",
        f"Just dropped it in your DM {clean_user}!",
        f"All done {clean_user}!",
        f"Sent {clean_user}!",
        f"Check your DM {clean_user}!",
        f"Delivered to your inbox {clean_user}!",
        f"Glad you liked it {clean_user}!",
        f"Sent directly to your inbox {clean_user}!",
    ]

    openers_without_user = [
        "Done!",
        "All set!",
        "Sent your way!",
        "Delivered!",
        "Awesome!",
        "Good choice!",
        "On its way!",
        "Just sent it over!",
        "Prompt dispatched!",
        "Ready for you!",
        "Check your inbox!",
        "You got it!",
        "Here you go!",
        "Just dropped it in your DM!",
        "All done!",
        "Sent!",
        "Check your DM!",
        "Delivered to your inbox!",
        "Glad you liked it!",
        "Sent directly to your inbox!",
    ]

    openers = openers_with_user if clean_user else openers_without_user

    action_phrases = [
        f"Sent the {kw} prompt directly to your DM." if kw else "Sent the full prompt directly to your DM.",
        "Check your DM for the exclusive prompt link & creative settings.",
        "Your private prompt access has been sent to your inbox.",
        "The complete prompt recipe is waiting in your DM.",
        "I've dispatched your VIP prompt access right now.",
        "Sent you the full prompt kit and creative workflow.",
        "Sent the access link straight to your direct messages.",
        "The AI prompt kit is now sitting in your inbox.",
        "Dropped the link and recipe right into your DMs.",
        "Your exclusive prompt kit is ready in your messages.",
        "Sent everything over to your direct messages.",
        "Check your messages for the complete prompt recipe.",
        "The full prompt recipe and camera settings are in your DM.",
        "Just delivered the step-by-step prompt kit to your inbox.",
        "Your prompt access is unlocked and waiting in your DM.",
        "Check your DM to copy the exact prompt recipe.",
        "Sent the scene workflow directly to your messages.",
        "All details and prompt settings are in your DM now.",
        "Your creative prompt kit has been sent to your inbox.",
        "Prompt delivered! Head over to your DM to grab it.",
    ]

    closers = [
        "🚀✨",
        "🔥🎯",
        "💫💡",
        "🌟🎬",
        "🤖✨",
        "📥✨",
        "💎🚀",
        "⚡🎯",
        "🎨✨",
        "🎬🔥",
        "✨🙌",
        "🚀💫",
    ]

    return f"{random.choice(openers)} {random.choice(action_phrases)} {random.choice(closers)}"


def get_dm_variation(keyword: str, video_id: str = "", author: str = "", prompt_text: str = "", title: str = "", platform: str = "instagram") -> str:
    """
    Clean, high-impact Private DM Engine:
    Delivers the actual full prompt prominently with minimal template fluff.
    """
    kw = (keyword or "VIP").upper().strip()
    clean_user = f"@{author.lstrip('@').strip()}" if author else "friend"
    clean_title = "".join(ch for ch in (title or "") if ch.isalnum() or ch in " .,!?-").strip()[:50] or "this episode"

    openers = [
        f'Hey {clean_user}! Here is your AI Cinema prompt for "{clean_title}":',
        f'Hi {clean_user}! As requested, here is your {kw} production prompt:',
        f'Hey {clean_user}! You\'ve unlocked the prompt recipe for "{clean_title}":',
        f'Awesome to connect {clean_user}! Here is your complete {kw} prompt:',
        f'Hey {clean_user}! Here is the exact scene prompt used for "{clean_title}":',
    ]

    closers = [
        "✨ Tip: Follow @visionvaultsai for upcoming episode prompts and workflows!\nHappy creating! 🎨🚀 — Vision Vault",
        "🔥 Stay tuned to @visionvaultsai for the next episode prompt drop!\nHappy generating! 🎬✨ — Team Vision Vault",
        "💎 Follow @visionvaultsai so you never miss upcoming cinematic scene prompts!\nEnjoy creating! 🚀 — Vision Vault",
    ]

    prompt_body = (prompt_text or "").strip()
    if not prompt_body or len(prompt_body) < 10:
        prompt_body = "Cinematic 9:16 vertical 8K dark fantasy sequence. Young warrior Arin stands courageously beside the ancient six-winged winter dragon atop glacial peaks, volumetric blizzard, radiant glowing runes, anamorphic 35mm lens, hyper-realistic detail."

    if len(prompt_body) > 800:
        candidate = prompt_body[:800]
        last_period = max(candidate.rfind(". "), candidate.rfind(".\n"), candidate.rfind("."))
        if last_period > 500:
            prompt_body = candidate[:last_period + 1]
        else:
            prompt_body = candidate[:797] + "..."

    import random
    return "\n".join([
        random.choice(openers),
        "",
        "🎬 PROMPT RECIPE:",
        f'"{prompt_body}"',
        "",
        random.choice(closers),
    ])


def get_youtube_reply(keyword: str, author: str, video_id: str = "", prompt_text: str = "", title: str = "") -> str:
    import urllib.parse
    kw = (keyword or "VIP").upper().strip()
    clean_author = "".join(c for c in author if c.isalnum() or c in "_-")
    user = f"@{clean_author}" if clean_author else "there"
    clean_title = "".join(c for c in title if c.isalnum() or c in " .,!?-").strip()[:50] if title else ""
    v_param = f"v={urllib.parse.quote_plus(video_id)}&" if video_id else ""
    t_param = f"&t={urllib.parse.quote_plus(clean_title)}" if clean_title else ""
    u_param = f"&u={clean_author}" if clean_author else ""
    reply_url = f"https://uaaf-automation.vercel.app/unlock?{v_param}k={urllib.parse.quote_plus(kw)}{t_param}&p=youtube{u_param}"

    templates = [
        f"Great choice {user}! Here is your {kw} prompt recipe: {reply_url} (Make sure to subscribe so you never miss the next part!) 🚀",
        f"Awesome! Your {kw} prompt is ready to copy here: {reply_url} (Subscribe for upcoming scene prompts!) ✨",
        f"Good pick {user}! Access the full prompt recipe here: {reply_url} 🎬",
        f"All set! Here is the exclusive {kw} prompt link: {reply_url} — don't forget to subscribe for more! 🔥",
        f"Glad you liked it {user}! Copy the exact prompt here: {reply_url} 🎯",
        f"Here you go! Your {kw} prompt is unlocked: {reply_url} (Subscribe for the next episode!) 💡",
        f"Great to have you here {user}! Get the prompt recipe here: {reply_url} 💫",
        f"Unlocked for you {user}! Link: ${reply_url} — subscribe for future AI Cinema workflows! 🌟",
    ]
    return random.choice(templates)


async def get_youtube_access_token():
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": Config.YOUTUBE_CLIENT_ID,
                    "client_secret": Config.YOUTUBE_CLIENT_SECRET,
                    "refresh_token": Config.YOUTUBE_REFRESH_TOKEN,
                    "grant_type": "refresh_token",
                },
            )
            if r.status_code == 200:
                return r.json().get("access_token")
    except Exception as e:
        log.warn(f"YouTube token refresh error: {e}")
    return None


async def poll_instagram():
    if not Config.META_ACCESS_TOKEN or not Config.META_IG_BUSINESS_ACCOUNT_ID:
        return
    token = Config.META_ACCESS_TOKEN
    ig_id = Config.META_IG_BUSINESS_ACCOUNT_ID
    page_id = Config.META_FB_PAGE_ID or Config.META_FB_PAGE_ID or Config.META_FB_PAGE_ID
    ig_id = Config.META_IG_BUSINESS_ACCOUNT_ID or Config.META_IG_BUSINESS_ACCOUNT_ID

    try:
        async with httpx.AsyncClient(timeout=25) as client:
            r = await client.get(
                f"https://graph.facebook.com/v20.0/{ig_id}/media",
                params={"fields": "id,caption,permalink", "access_token": token, "limit": 25},
            )
            if r.status_code != 200:
                return
            media_items = r.json().get("data", [])

            for m in media_items:
                m_id = m["id"]
                caption = m.get("caption", "")

                c_resp = await client.get(
                    f"https://graph.facebook.com/v20.0/{m_id}/comments",
                    params={
                        "fields": "id,text,from,timestamp,parent_id,replies{id,from}",
                        "access_token": token,
                        "limit": 30,
                    },
                )
                if c_resp.status_code != 200:
                    continue
                comments = c_resp.json().get("data", [])

                for c in comments:
                    c_id = c["id"]
                    raw_text = c.get("text") or ""
                    author_name = (c.get("from", {}).get("username") or "").lower()

                    # Ignore comments from the brand channel itself
                    if "visionvault" in author_name:
                        save_replied_id(c_id)
                        continue

                    if c_id in REPLIED_COMMENTS:
                        continue

                    # Check if already replied
                    replies_data = c.get("replies", {}).get("data", [])
                    if len(replies_data) > 0:
                        save_replied_id(c_id)
                        continue

                    keyword, video_id, prompt_to_send, vid_title = detect_keyword(raw_text, caption, m_id)
                    if not keyword:
                        continue

                    log.info(f"  💬 Found trigger comment on Instagram (ID: {c_id}, User: @{author_name}): '{raw_text}' → Keyword: {keyword} (Video: {video_id})")

                    # ── DIRECT INSTANT DM DELIVERY ON TRIGGER COMMENT ──
                    user_key = (author_name or c_id).lower().strip()
                    mark_verified(user_key)
                    save_replied_id(c_id)

                    # Anti-Ban Safe Delay (2 to 4 seconds jitter)
                    await asyncio.sleep(random.uniform(2.0, 4.0))

                    # 1. Send Direct Private DM via Meta Messages API
                    dm_text = get_dm_variation(keyword, video_id, author_name, prompt_to_send, vid_title)
                    try:
                        dm_resp = await client.post(
                            f"https://graph.facebook.com/v20.0/{page_id}/messages",
                            json={"recipient": {"comment_id": c_id}, "message": {"text": dm_text}},
                            params={"access_token": token},
                        )
                        if dm_resp.status_code in (200, 201):
                            log.info(f"  📩 Direct Private Instagram DM Sent to @{author_name} for comment {c_id}")
                        else:
                            log.warn(f"Instagram DM failed ({dm_resp.status_code}): {dm_resp.text[:150]}")
                    except Exception as dm_err:
                        log.warn(f"Instagram DM exception: {dm_err}")

                    # 2. Reply to Public Comment (Randomized Short English Confirmation)
                    confirmed_text = get_dm_confirmation_comment(author_name, "instagram", keyword)
                    try:
                        r_post = await client.post(
                            f"https://graph.facebook.com/v20.0/{c_id}/replies",
                            params={"message": confirmed_text, "access_token": token},
                        )
                        if r_post.status_code in (200, 201):
                            log.info(f"  ✅ Auto-replied to Instagram comment {c_id} with delivery confirmation")
                        else:
                            log.warn(f"Instagram reply failed ({r_post.status_code}): {r_post.text[:150]}")
                    except Exception as r_err:
                        log.warn(f"Instagram reply exception: {r_err}")


    except Exception as e:
        log.warn(f"Instagram poller error: {e}")


async def poll_youtube():
    yt_token = await get_youtube_access_token()
    if not yt_token:
        return

    # Dynamically extract all published YouTube video IDs
    video_ids = [
        "fiJ2ZiWE0Q0",  # Fortuner
        "FZCGFRqzo6g",  # Paisa
        "qz5Npx-2l4Q",  # Chain
        "n19SgGtn5tI",  # Superbike
        "n1trcyfE7BY",  # Child story final
        "xKqk6IyRhcs",  # Tamatar final
        "uPC4-t_JZH0",  # Ameer Tamatar Part 2
        "1kHSxZABZJI",  # Bhindi Aalu Part 2
        "r7OKh80nTKg",  # Ocean Baby
        "3yMh87zY9jo",
    ]
    if os.path.exists(SCHEDULE_FILE):
        try:
            with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
                for item in json.load(f):
                    yt_res = item.get("published_platforms", {}).get("youtube", {})
                    y_id = yt_res.get("media_id") or ""
                    if y_id and y_id not in video_ids:
                        video_ids.insert(0, y_id)
        except Exception:
            pass

    try:
        async with httpx.AsyncClient(timeout=25) as client:
            for vid in video_ids[:20]:
                r = await client.get(
                    "https://www.googleapis.com/youtube/v3/commentThreads",
                    params={"part": "snippet,replies", "videoId": vid, "access_token": yt_token, "maxResults": 25},
                )
                if r.status_code != 200:
                    continue
                items = r.json().get("items", [])

                for it in items:
                    c_id = it["id"]
                    top = it["snippet"]["topLevelComment"]["snippet"]
                    text = (top.get("textDisplay") or "").strip()
                    author = top.get("authorDisplayName", "Friend")

                    # Ignore comments from channel itself
                    if "vision" in author.lower():
                        save_replied_id(c_id)
                        continue

                    if c_id in REPLIED_COMMENTS:
                        continue

                    # If already has ANY replies on YouTube, skip immediately
                    if (it.get("snippet", {}).get("totalReplyCount", 0)) > 0:
                        save_replied_id(c_id)
                        continue

                    keyword, video_id, prompt_to_send, vid_title = detect_keyword(text, "", vid)
                    if not keyword:
                        continue

                    log.info(f"  💬 Found trigger comment on YouTube (Video: {vid}, Comment: {c_id}): '{text}' → Keyword: {keyword} (Video: {video_id})")

                    save_replied_id(c_id)

                    # Anti-Ban Safe Delay (3 to 6 seconds jitter)
                    await asyncio.sleep(random.uniform(3.0, 6.0))

                    reply_msg = get_youtube_reply(keyword, author, video_id or vid, prompt_to_send, vid_title)
                    r_post = await client.post(
                        "https://www.googleapis.com/youtube/v3/comments?part=snippet",
                        headers={"Authorization": f"Bearer {yt_token}", "Content-Type": "application/json"},
                        json={"snippet": {"parentId": c_id, "textOriginal": reply_msg}},
                    )
                    if r_post.status_code in (200, 201):
                        log.info(f"  ✅ Auto-replied to YouTube comment {c_id}")
    except Exception as e:
        log.warn(f"YouTube poller error: {e}")


async def poll_facebook():
    if not Config.META_ACCESS_TOKEN or not Config.META_FB_PAGE_ID:
        return
    token = Config.META_ACCESS_TOKEN
    page_id = Config.META_FB_PAGE_ID or Config.META_FB_PAGE_ID or Config.META_FB_PAGE_ID
    ig_id = Config.META_IG_BUSINESS_ACCOUNT_ID or Config.META_IG_BUSINESS_ACCOUNT_ID

    try:
        async with httpx.AsyncClient(timeout=25) as client:
            # Query /videos endpoint only to prevent duplicate processing from reels/posts
            endpoints = [
                f"https://graph.facebook.com/v20.0/{page_id}/videos",
                f"https://graph.facebook.com/v20.0/{page_id}/published_posts",
            ]
            for ep in endpoints:
                try:
                    r = await client.get(
                        ep,
                        params={"fields": "id,message,description,title,comments{id,message,from,timestamp,can_reply_privately,can_comment,comments{id,message,from}}", "access_token": token, "limit": 20},
                    )
                    if r.status_code != 200:
                        continue
                    items = r.json().get("data", [])
                    for item in items:
                        item_desc = item.get("message", "") or item.get("description", "") or item.get("title", "")
                        comments = item.get("comments", {}).get("data", [])
                        for c in comments:
                            c_id = c.get("id")
                            if not c_id or c_id in REPLIED_COMMENTS:
                                continue
                            raw_msg = c.get("message", "")
                            author_name = c.get("from", {}).get("name") or "Friend"

                            # Ignore bot's own replies or comments containing our domain/gratitude/bot text
                            if (
                                "vision" in author_name.lower()
                                or "uaaf-automation" in raw_msg.lower()
                                or "shukriya" in raw_msg.lower()
                                or "pehle" in raw_msg.lower()
                                or "bhej diya" in raw_msg.lower()
                            ):
                                save_replied_id(c_id)
                                continue

                            # If comment already has sub-replies, skip!
                            sub_comments = c.get("comments", {}).get("data", [])
                            if len(sub_comments) > 0:
                                save_replied_id(c_id)
                                continue

                            can_reply = c.get("can_reply_privately", False)
                            can_comment = c.get("can_comment", False)

                            keyword, video_id, prompt_to_send, vid_title = detect_keyword(raw_msg, item_desc, item.get("id"))
                            if not keyword:
                                continue

                            log.info(f"  💬 Found trigger comment on Facebook ({c_id}, User: {author_name}): '{raw_msg}' → Keyword: {keyword} (Video: {video_id})")

                            if not can_reply and not can_comment:
                                log.info(f"  ℹ️ Facebook comment {c_id} is from Page Admin / self — Meta disables DM to own account.")
                                save_replied_id(c_id)
                                continue

                            # ── DIRECT INSTANT DM DELIVERY ON TRIGGER COMMENT ──
                            user_key = (author_name or c_id).lower().strip()
                            mark_verified(user_key)
                            save_replied_id(c_id)

                            await asyncio.sleep(random.uniform(2.0, 4.0))

                            fb_vid = video_id or item.get("id") or ""
                            # 1. Send Messenger Private Reply DM (only if can_reply_privately is True)
                            dm_sent = False
                            if can_reply:
                                dm_text = get_dm_variation(keyword, fb_vid, author_name, prompt_to_send, vid_title)
                                try:
                                    dm_resp = await client.post(
                                        f"https://graph.facebook.com/v20.0/{page_id}/messages",
                                        json={"recipient": {"comment_id": c_id}, "message": {"text": dm_text}},
                                        params={"access_token": token},
                                    )
                                    if dm_resp.status_code in (200, 201):
                                        dm_sent = True
                                        log.info(f"  📩 Direct Private Messenger DM Sent to {author_name} for comment {c_id}")
                                    else:
                                        log.warn(f"Facebook DM not available ({dm_resp.status_code}): {dm_resp.text[:150]}")
                                except Exception as dm_err:
                                    log.warn(f"Facebook DM exception: {dm_err}")

                            # 2. Public Comment Reply: "Bhai bhej diya! Check your DM! 🚀✨"
                            if can_comment:
                                confirmed_text = get_dm_confirmation_comment(author_name, "facebook", keyword)
                                try:
                                    r_post = await client.post(
                                        f"https://graph.facebook.com/v20.0/{c_id}/comments",
                                        params={"message": confirmed_text, "access_token": token},
                                    )
                                    if r_post.status_code in (200, 201):
                                        log.info(f"  ✅ Auto-replied confirmed DM to Facebook comment {c_id}")
                                    else:
                                        log.warn(f"Facebook reply failed ({r_post.status_code}): {r_post.text[:150]}")
                                except Exception as r_err:
                                    log.warn(f"Facebook reply exception: {r_err}")
                except Exception as ep_err:
                    log.warn(f"Facebook endpoint error ({ep}): {ep_err}")
    except Exception as e:
        log.warn(f"Facebook poller error: {e}")

        log.warn(f"Facebook poller error: {e}")


async def main_worker_loop():
    log.info("🤖 UAAF Anti-Ban 24/7 Human-Like Auto-Comment Engine Running...")
    keywords = [it.get("comment_keyword") for it in load_schedule_items() if it.get("comment_keyword")]
    log.info(f"   Keywords tracked: {keywords} + PART 2 / PROMPT variations")
    log.info("   Platforms active: Instagram (DM + Reply), Facebook Page (Messenger DM + Reply), YouTube (Public Reply)")
    while True:
        try:
            await poll_instagram()
            await poll_facebook()
            await poll_youtube()
        except Exception as e:
            log.warn(f"Worker iteration exception: {e}")
        # Safe 20s poller cadence
        await asyncio.sleep(20)


if __name__ == "__main__":
    asyncio.run(main_worker_loop())

