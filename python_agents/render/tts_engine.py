"""
UAAF TTS Engine — Uses edge-tts (FREE, no API key needed).
Generates premium neural voiceovers via Microsoft Edge's TTS service.

Available premium voices (no cost):
- en-US-AriaNeural (female, warm, premium)
- en-US-GuyNeural (male, confident)
- en-GB-SoniaNeural (British female, luxury)
- en-US-JennyNeural (female, conversational)

Output: .mp3 file at the specified path.
"""
import asyncio
import edge_tts
from config import Config
from utils.logger import log
from datetime import datetime, timezone
import os


async def generate_voiceover(
    text: str,
    output_path: str = None,
    voice: str = None,
    rate: str = "+0%",
    volume: str = "+0%"
) -> str:
    """
    Generate a voiceover .mp3 using edge-tts (100% free, no API key).

    Args:
        text: The script to narrate
        output_path: Where to save the .mp3 (auto-generated if None)
        voice: Voice ID (default: en-US-AriaNeural)
        rate: Speech rate adjustment (e.g. "-10%" for slower, luxury pacing)
        volume: Volume adjustment

    Returns:
        Path to the generated .mp3 file
    """
    voice = voice or Config.EDGE_TTS_VOICE
    Config.ensure_dirs()

    if output_path is None:
        filename = f"voiceover_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.mp3"
        output_path = os.path.join(Config.AUDIO_DIR, filename)

    log.info(f"TTS Engine: generating voiceover with {voice}")
    log.info(f"  Text length: {len(text)} chars")
    log.info(f"  Rate: {rate} (slower = more luxury)")

    # Create TTS communicator
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        volume=volume,
    )

    # Generate audio
    await communicate.save(output_path)

    # Get file size
    size_kb = os.path.getsize(output_path) / 1024
    log.info(f"TTS Engine: voiceover saved to {output_path} ({size_kb:.1f} KB)")

    return output_path


async def generate_scene_voiceovers(scenes: list, output_dir: str = None) -> list:
    """
    Generate individual voiceover clips for each scene.
    Returns list of {scene_id, audio_path, duration_sec}.
    """
    output_dir = output_dir or Config.AUDIO_DIR
    Config.ensure_dirs()
    os.makedirs(output_dir, exist_ok=True)

    results = []
    for scene in scenes:
        text = scene.get("voiceover_text", "")
        if not text.strip():
            continue

        scene_id = scene["id"]
        path = os.path.join(output_dir, f"scene_{scene_id}.mp3")

        # Use slower rate for luxury feel (-8% = more deliberate pacing)
        await generate_voiceover(text, path, rate="-8%")

        results.append({
            "scene_id": scene_id,
            "audio_path": path,
            "text": text,
        })

    log.info(f"TTS Engine: generated {len(results)} scene voiceovers")
    return results


# ── Premium voice presets ──
VOICES = {
    "luxury_female": "en-GB-SoniaNeural",     # British, sophisticated
    "luxury_male": "en-US-GuyNeural",          # Confident, warm
    "cinematic_female": "en-US-AriaNeural",    # Default, premium
    "conversational": "en-US-JennyNeural",     # Natural, friendly
    "narrator": "en-US-DavisNeural",           # Documentary style
}


if __name__ == "__main__":
    # Test: generate a sample voiceover
    test_text = "Most coffee is noise. This one is silence. Single-origin Ethiopian beans, hand-roasted in cedar smoke for 72 hours."
    path = asyncio.run(generate_voiceover(test_text, rate="-10%"))
    print(f"Voiceover generated: {path}")
