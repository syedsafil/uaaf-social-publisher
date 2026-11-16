"""
UAAF Asset Fetcher — PEXELS VIDEO API
═══════════════════════════════════════════════════════════════
Replaces Pollinations.ai (static images) with Pexels Video API.
Downloads REAL 4K/HD cinematic moving footage for each scene.

Pexels API: 100% FREE, 200 requests/hour, no attribution required.
Get key: https://www.pexels.com/api/

This fetches ACTUAL VIDEO CLIPS (.mp4), not images.
The video compiler then stitches these clips together.
═══════════════════════════════════════════════════════════════
"""
import os
import sys
import httpx
import asyncio
from typing import List, Dict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from utils.logger import log

PEXELS_VIDEO_API = "https://api.pexels.com/videos/search"


async def fetch_scene_videos(scenes: List[Dict]) -> List[Dict]:
    """
    Fetch real video footage for each scene from Pexels Video API.

    Args:
        scenes: List of scene dicts from research_agent
            Each scene must have "pexels_search_query" field

    Returns:
        List of {scene_id, video_path, duration_sec, camera_movement, text_overlay}
    """
    Config.ensure_dirs()

    # Pexels API key — add to .env as PEXELS_API_KEY
    pexels_key = os.getenv("PEXELS_API_KEY", "")

    if not pexels_key:
        log.warn("PEXELS_API_KEY not set in .env. Using fallback image mode.")
        log.warn("Get free key at: https://www.pexels.com/api/")
        return await _fallback_images(scenes)

    log.info(f"Asset Fetcher: fetching video clips for {len(scenes)} scenes from Pexels")

    results = []
    headers = {"Authorization": pexels_key}

    for i, scene in enumerate(scenes):
        query = scene.get("pexels_search_query", scene.get("visual_description", "luxury cinematic"))
        scene_id = scene.get("id", i + 1)
        duration = scene.get("duration_sec", 3)
        movement = scene.get("camera_movement", "zoom_in")
        overlay = scene.get("text_overlay", "")

        log.info(f"  Scene {scene_id}: searching Pexels for '{query}'...")

        try:
            # Search Pexels Video API
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    PEXELS_VIDEO_API,
                    headers=headers,
                    params={
                        "query": query,
                        "per_page": 5,        # Get 5 results, pick best
                        "orientation": "portrait",  # 9:16 vertical for Shorts/Reels
                        "size": "large",       # HD/4K quality
                    }
                )

                if resp.status_code != 200:
                    log.warn(f"  Pexels API error: {resp.status_code} — using fallback")
                    results.extend(await _fallback_images([scene]))
                    continue

                data = resp.json()
                videos = data.get("videos", [])

                if not videos:
                    log.warn(f"  No videos found for '{query}' — trying broader search")
                    # Try broader search
                    async with httpx.AsyncClient(timeout=30) as client:
                        resp = await client.get(
                            PEXELS_VIDEO_API,
                            headers=headers,
                            params={
                                "query": " ".join(query.split()[:2]),  # First 2 words only
                                "per_page": 3,
                                "orientation": "portrait",
                                "size": "large",
                            }
                        )
                        if resp.status_code == 200:
                            videos = resp.json().get("videos", [])

                if not videos:
                    log.warn(f"  Still no videos — using fallback image")
                    results.extend(await _fallback_images([scene]))
                    continue

                # Pick the best quality video file (prefer HD)
                best_video = videos[0]
                best_file = None

                for vf in best_video.get("video_files", []):
                    # Prefer 1080p or closest
                    if vf.get("height", 0) >= 1920 or vf.get("width", 0) >= 1080:
                        best_file = vf
                        break
                    if vf.get("height", 0) >= 1080:
                        best_file = vf

                if not best_file and best_video.get("video_files"):
                    best_file = best_video["video_files"][0]

                if not best_file:
                    log.warn(f"  No video file in Pexels result — using fallback")
                    results.extend(await _fallback_images([scene]))
                    continue

                # Download the video clip
                video_url = best_file["link"]
                clip_path = os.path.join(Config.VIDEO_DIR, f"scene_{scene_id}.mp4")

                log.info(f"  Downloading: {video_url[:80]}...")
                async with httpx.AsyncClient(timeout=120) as client:
                    resp = await client.get(video_url)
                    with open(clip_path, "wb") as f:
                        f.write(resp.content)

                file_size = os.path.getsize(clip_path) / (1024 * 1024)
                log.info(f"  Downloaded scene {scene_id}: {file_size:.1f} MB")

                results.append({
                    "scene_id": scene_id,
                    "video_path": clip_path,
                    "duration_sec": duration,
                    "camera_movement": movement,
                    "text_overlay": overlay,
                    "source": "pexels",
                })

        except Exception as e:
            log.error(f"  Scene {scene_id} fetch failed: {e}")
            results.extend(await _fallback_images([scene]))

    log.info(f"Asset Fetcher: {len(results)} clips ready")
    return results


async def _fallback_images(scenes: List[Dict]) -> List[Dict]:
    """
    Fallback: if Pexels API not available, download static images from
    Pollinations.ai (free, no key). These are NOT as good as real video
    but prevent pipeline crash.
    """
    results = []
    for scene in scenes:
        scene_id = scene.get("id", 1)
        prompt = scene.get("visual_description", "luxury product cinematic")
        img_path = os.path.join(Config.VIDEO_DIR, f"scene_{scene_id}.jpg")

        url = f"https://image.pollinations.ai/prompt/{prompt}?width=1080&height=1920&seed={scene_id * 42}&nologo=true"

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.get(url)
                with open(img_path, "wb") as f:
                    f.write(resp.content)

            results.append({
                "scene_id": scene_id,
                "image_path": img_path,
                "duration_sec": scene.get("duration_sec", 3),
                "camera_movement": scene.get("camera_movement", "zoom_in"),
                "text_overlay": scene.get("text_overlay", ""),
                "source": "pollinations_fallback",
            })
            log.info(f"  Fallback image for scene {scene_id}: {prompt[:40]}")

        except Exception as e:
            log.error(f"  Fallback image failed: {e}")

    return results
