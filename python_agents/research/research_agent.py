"""
UAAF Research Agent — GROQ OFFICIAL SDK (FIXED)
═══════════════════════════════════════════════════════════════
FIXES:
1. Uses official `groq` Python SDK (not httpx — was 404 error)
2. datetime.utcnow() → datetime.now(timezone.utc)
3. Sambanova fallback removed
4. All prompts include "json" word (Groq strict requirement)
═══════════════════════════════════════════════════════════════
"""
import os
import sys
import json
import asyncio
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from utils.logger import log

GROQ_MODEL = "groq/compound"
FALLBACK_MODELS = ["groq/compound", "groq/compound-mini", "qwen/qwen3.8-27b", "openai/gpt-oss-20b"]

RESEARCH_SYSTEM_PROMPT = """You are the Lead Creative Director & Viral Algorithm Specialist for the Universal AI Ad Factory (UAAF).
Your job: engineer hyper-viral, luxury short-form videos tailored for maximum algorithmic distribution on TikTok FYP, Instagram Reels, and YouTube Shorts.

VIRAL ALGORITHM CONSTITUTION (STRICT LAWS):
1. HOOK RATE (<3s): The first 3 seconds MUST create an irresistible curiosity gap, pattern-interrupt, or high-status contrarian insight. Max 6 words on screen for the hook.
2. VISUAL PACING (2.5s - 3.2s per scene): Fast-paced, high-end cinematic stock queries with dynamic camera motion (macro zoom, slow motion, drone sweep).
3. COMMENT-DRIVEN ENGAGEMENT LOOP: Every script MUST end with a high-conversion call to action prompting the viewer to comment 'KIT' or 'GET' to trigger the automated DM funnel.
4. HIGH RETENTION (<22s total duration): Punchy, hypnotic narration with zero fluff. Every word must hold attention.
5. SEO & HASHTAG MATRIX: Include 5 hyper-targeted viral tags (2 broad trending, 2 high-intent niche, 1 brand).

IMPORTANT: You must always respond with valid JSON. The word json must appear in your instructions."""

CONCEPT_USER_PROMPT = """Generate a high-conversion viral video concept engineered for TikTok, Reels & Shorts in the niche: {niche}

You must respond with valid json. Here is the exact json structure required:

{{
  "niche": "{niche}",
  "title": "<magnetic 4-6 word SEO title>",
  "hook": "<powerful 3-5 word curiosity hook, e.g., 'The Silent Luxury Rule'>",
  "caption": "<evocative 1-2 sentence caption followed by: Comment 'KIT' below to unlock the private prompt & recipe in your DMs 👇>",
  "comment_keyword": "KIT",
  "cta": "Comment 'KIT' below to unlock the VIP kit.",
  "hashtags": ["#luxury", "#viral", "#fyp", "#reels", "#lifestyle"],
  "scenes": [
    {{
      "id": 1,
      "duration_sec": 3,
      "visual_description": "<high-end 4K visual description for Pexels search>",
      "pexels_search_query": "<precision 2-4 word stock search term, e.g., 'luxury coffee pour 4k' or 'espresso gold crema'>",
      "voiceover_text": "<punchy narration opening that stops scrolling>",
      "text_overlay": "<maximum 5 bold words on screen>",
      "camera_movement": "zoom_in"
    }},
    {{
      "id": 2,
      "duration_sec": 3,
      "visual_description": "<cinematic macro detail scene>",
      "pexels_search_query": "<stock search query>",
      "voiceover_text": "<educational/intriguing insight>",
      "text_overlay": "<bold on-screen text>",
      "camera_movement": "pan_right"
    }},
    {{
      "id": 3,
      "duration_sec": 3,
      "visual_description": "<luxury aesthetic mood scene>",
      "pexels_search_query": "<stock search query>",
      "voiceover_text": "<climax of the tip or sensory feeling>",
      "text_overlay": "<bold on-screen text>",
      "camera_movement": "ken_burns"
    }},
    {{
      "id": 4,
      "duration_sec": 3,
      "visual_description": "<final high-status outcome scene>",
      "pexels_search_query": "<stock search query>",
      "voiceover_text": "<smooth CTA driving comment engagement>",
      "text_overlay": "Comment 'KIT' Below",
      "camera_movement": "zoom_out"
    }}
  ],
  "voiceover_full": "<seamless complete voiceover script, 14-18 seconds spoken>",
  "background_music_mood": "<cinematic|luxury|ambient>",
  "estimated_duration_sec": 16,
  "quality_prediction": {{
    "curiosity_score": 96,
    "luxury_score": 98,
    "viral_potential": 94
  }},
  "prompt_dna": "<the exact visual generation prompt to deliver to user upon comment>"
}}

Generate the json response now:"""


async def research_trend(niche="auto"):
    """
    Main entry point: research a trending niche and generate a video concept.
    Returns structured JSON that feeds into the render pipeline.
    """
    Config.validate()
    Config.ensure_dirs()

    if niche == "auto":
        niche = await _select_trending_niche()

    log.info(f"Research Agent: generating concept for niche '{niche}'")

    concept = await _call_groq(
        system=RESEARCH_SYSTEM_PROMPT,
        user=CONCEPT_USER_PROMPT.format(niche=niche)
    )

    concept["generated_at"] = datetime.now(timezone.utc).isoformat()
    concept["agent"] = "research_agent_v1"
    concept["model"] = GROQ_MODEL

    # Save to output
    filename = f"concept_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join(Config.SCRIPTS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(concept, f, indent=2, ensure_ascii=False)

    log.info(f"Research Agent: concept saved to {filepath}")
    log.info(f"  Title: {concept.get('title')}")
    log.info(f"  Hook: {concept.get('hook')}")
    log.info(f"  Scenes: {len(concept.get('scenes', []))}")

    return concept


async def _select_trending_niche():
    """
    Ask LLM to pick the best trending luxury niche.
    FIXED: Now returns JSON (Groq requirement).
    """
    system = "You are a trend analyst. You must respond with valid json. The word json is in your instructions."
    user = """Pick the single best trending luxury micro-niche for short-form video today.
Choose from: luxury coffee, horology, fragrance, footwear, furniture, spirits, metalwork, textiles.
Respond with this json format: {"niche": "<your choice>"}"""

    try:
        result = await _call_groq(system=system, user=user)
        niche = result.get("niche", "luxury coffee")
        log.info(f"Selected trending niche: {niche}")
        return niche
    except Exception as e:
        log.warn(f"Niche selection failed ({e}), using default")
        return "luxury coffee"


async def _call_groq(system, user):
    """
    Call Groq API using OFFICIAL groq Python SDK with model fallback.
    """
    if not Config.GROQ_API_KEY or Config.GROQ_API_KEY.startswith("gsk_your"):
        raise ValueError("GROQ_API_KEY not set in .env. Get free key at https://console.groq.com")

    try:
        from groq import Groq
    except ImportError:
        log.error("groq package not installed. Run: pip install groq")
        raise

    client = Groq(api_key=Config.GROQ_API_KEY)
    loop = asyncio.get_event_loop()

    last_error = None
    for model in FALLBACK_MODELS:
        try:
            def _sync_call(m=model):
                response = client.chat.completions.create(
                    model=m,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=0.85,
                    max_tokens=2000,
                    response_format={"type": "json_object"},
                )
                return response.choices[0].message.content

            content = await loop.run_in_executor(None, _sync_call)
            return json.loads(content)
        except json.JSONDecodeError as e:
            log.error(f"JSON parse failed for model '{model}': {e}")
            last_error = e
        except Exception as e:
            last_error = e
            log.warn(f"Groq model '{model}' failed ({e}), trying next fallback...")

    raise RuntimeError(f"All Groq models failed. Last error: {last_error}")


if __name__ == "__main__":
    result = asyncio.run(research_trend("luxury coffee"))
    print(json.dumps(result, indent=2, ensure_ascii=False))
