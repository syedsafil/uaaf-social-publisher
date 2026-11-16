"""Video checks shared by Reels, TikTok and YouTube Shorts publishers."""
import json
import subprocess
from pathlib import Path
from typing import Dict


def inspect_video(path: str) -> Dict:
    """Return dimensions and duration without loading the video into memory."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Video file not found: {path}")
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height:format=duration", "-of", "json", str(source)],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(probe.stdout)
    stream = (data.get("streams") or [{}])[0]
    return {"width": int(stream.get("width") or 0), "height": int(stream.get("height") or 0),
            "duration_seconds": float((data.get("format") or {}).get("duration") or 0)}


def short_form_check(path: str) -> Dict:
    """Validate YouTube Shorts eligibility: square/vertical and at most 3 minutes."""
    info = inspect_video(path)
    problems = []
    if info["width"] <= 0 or info["height"] <= 0:
        problems.append("Could not read the video dimensions")
    elif info["height"] < info["width"]:
        problems.append("YouTube Shorts must be square or vertical; this file is landscape")
    if info["duration_seconds"] <= 0:
        problems.append("Could not read the video duration")
    elif info["duration_seconds"] > 180:
        problems.append("YouTube Shorts must be 3 minutes or shorter")
    return {**info, "is_short_eligible": not problems, "problems": problems}
