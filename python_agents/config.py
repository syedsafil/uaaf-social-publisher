"""
UAAF Config — Loads all environment variables.
Windows-safe: works with both SQLite (local) and PostgreSQL (production).
LinkedIn removed — we focus on IG, FB, TikTok, YouTube, X only.
"""
import os
from dotenv import load_dotenv

_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(_env_path):
    load_dotenv(_env_path)
else:
    load_dotenv()


def _supabase_url(value: str) -> str:
    """Accept either a full Supabase URL or the project reference from .env."""
    value = value.strip().strip('"').strip("'")
    if value and not value.startswith(("https://", "http://")):
        return f"https://{value}.supabase.co"
    return value.rstrip("/")


class Config:
    # ── DATABASE ──
    DATABASE_URL = os.getenv("DATABASE_URL", "file:./dev.db")

    # ── NEXT.JS ──
    NEXTAUTH_URL = os.getenv("NEXTAUTH_URL", "http://localhost:3000")
    NEXTAUTH_SECRET = os.getenv("NEXTAUTH_SECRET", "uaaf-secret-dev")
    NEXT_PUBLIC_APP_URL = os.getenv("NEXT_PUBLIC_APP_URL", "http://localhost:3000")

    # ── LLM APIs ──
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "groq/compound-mini")
    SAMBANOVA_API_KEY = os.getenv("SAMBANOVA_API_KEY", "")
    ZAI_API_KEY = os.getenv("ZAI_API_KEY", "")

    # ── RESEND (Email approval) ──
    RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
    CHAIRMAN_EMAIL = os.getenv("CHAIRMAN_EMAIL", "")

    # ── META (Instagram + Facebook) ──
    META_APP_ID = os.getenv("META_APP_ID", "")
    META_APP_SECRET = os.getenv("META_APP_SECRET", "")
    META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
    META_IG_BUSINESS_ACCOUNT_ID = os.getenv("META_IG_BUSINESS_ACCOUNT_ID", "")
    META_FB_PAGE_ID = os.getenv("META_FB_PAGE_ID", "")
    META_WEBHOOK_VERIFY_TOKEN = os.getenv("META_WEBHOOK_VERIFY_TOKEN", "uaaf_webhook_verify_token_2024")

    # ── TikTok ──
    TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY", "")
    TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "")
    TIKTOK_ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "")
    TIKTOK_REFRESH_TOKEN = os.getenv("TIKTOK_REFRESH_TOKEN", "")
    TIKTOK_DIRECT_POST_ENABLED = os.getenv("TIKTOK_DIRECT_POST_ENABLED", "false").lower() == "true"

    # ── YouTube ──
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
    YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID", "")
    YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET", "")
    YOUTUBE_REFRESH_TOKEN = os.getenv("YOUTUBE_REFRESH_TOKEN", "")
    YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "")
    YOUTUBE_PRIVACY_STATUS = os.getenv("YOUTUBE_PRIVACY_STATUS", "private")

    # ── X.com / Twitter ──
    X_API_KEY = os.getenv("X_API_KEY", "") or os.getenv("TWITTER_API_KEY", "")
    X_API_SECRET = os.getenv("X_API_SECRET", "") or os.getenv("TWITTER_API_SECRET", "")
    X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN", "") or os.getenv("TWITTER_ACCESS_TOKEN", "")
    X_ACCESS_TOKEN_SECRET = (
        os.getenv("X_ACCESS_TOKEN_SECRET", "")
        or os.getenv("TWITTER_ACCESS_SECRET", "")
        or os.getenv("TWITTER_ACCESS_TOKEN_SECRET", "")
    )
    X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN", "") or os.getenv("TWITTER_BEARER_TOKEN", "")

    # ── LinkedIn ──
    LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN", "")

    # ── LEMON SQUEEZY (Pakistan-supported payment) ──
    LEMONSQUEEZY_API_KEY = os.getenv("LEMONSQUEEZY_API_KEY", "")
    LEMONSQUEEZY_WEBHOOK_SECRET = os.getenv("LEMONSQUEEZY_WEBHOOK_SECRET", "")
    LEMONSQUEEZY_STORE_ID = os.getenv("LEMONSQUEEZY_STORE_ID", "")
    LEMONSQUEEZY_VARIANT_ID = os.getenv("LEMONSQUEEZY_VARIANT_ID", "")
    LEMONSQUEEZY_PRODUCT_NAME = os.getenv("LEMONSQUEEZY_PRODUCT_NAME", "UAAF Premium Kit")
    PAYMENT_AMOUNT = int(os.getenv("PAYMENT_AMOUNT", "20"))
    PAYMENT_CURRENCY = os.getenv("PAYMENT_CURRENCY", "USD")

    # ── COMMENT-TO-DM FUNNEL ──
    DM_TRIGGER_KEYWORD = os.getenv("DM_TRIGGER_KEYWORD", "KIT")
    DM_COOLDOWN_SECONDS = int(os.getenv("DM_COOLDOWN_SECONDS", "3600"))

    # ── SUPABASE (Cloud storage — FREE 1GB) ──
    SUPABASE_URL = _supabase_url(os.getenv("SUPABASE_URL", ""))
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    SUPABASE_BUCKET_NAME = os.getenv("SUPABASE_BUCKET_NAME", "uaaf-media")

    # ── S3/R2 (Alternative storage) ──
    S3_ENDPOINT = os.getenv("S3_ENDPOINT", "")
    S3_ACCESS_KEY_ID = os.getenv("S3_ACCESS_KEY_ID", "")
    S3_SECRET_ACCESS_KEY = os.getenv("S3_SECRET_ACCESS_KEY", "")
    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "")
    S3_REGION = os.getenv("S3_REGION", "auto")
    PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")

    # ── WEBHOOK ──
    WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "3001"))
    WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "http://localhost:3000")

    # ── TELEGRAM ──
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

    # ── VIDEO CONFIG ──
    FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")
    EDGE_TTS_VOICE = os.getenv("EDGE_TTS_VOICE", "en-US-AriaNeural")
    VIDEO_WIDTH = int(os.getenv("VIDEO_WIDTH", "1080"))
    VIDEO_HEIGHT = int(os.getenv("VIDEO_HEIGHT", "1920"))
    VIDEO_FPS = int(os.getenv("VIDEO_FPS", "30"))
    VIDEO_DURATION = int(os.getenv("VIDEO_DURATION", "18"))

    # ── AUTONOMY ──
    ENABLE_AUTO_PUBLISH = os.getenv("ENABLE_AUTO_PUBLISH", "false") == "true"
    QUALITY_THRESHOLD = int(os.getenv("QUALITY_THRESHOLD", "85"))
    ENABLE_FOLLOW_GATE = os.getenv("ENABLE_FOLLOW_GATE", "true") == "true"
    ENABLE_LLM_REPLIES = os.getenv("ENABLE_LLM_REPLIES", "true") == "true"
    AUTO_GENERATE_TIME = os.getenv("AUTO_GENERATE_TIME", "10:00")

    # ── PATHS ──
    OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
    SCRIPTS_DIR = os.path.join(OUTPUT_DIR, "scripts")
    AUDIO_DIR = os.path.join(OUTPUT_DIR, "audio")
    VIDEO_DIR = os.path.join(OUTPUT_DIR, "video")
    FINAL_DIR = os.path.join(OUTPUT_DIR, "final")

    @classmethod
    def ensure_dirs(cls):
        """Create output directories if they don't exist."""
        for d in [cls.OUTPUT_DIR, cls.SCRIPTS_DIR, cls.AUDIO_DIR, cls.VIDEO_DIR, cls.FINAL_DIR]:
            os.makedirs(d, exist_ok=True)

    @classmethod
    def validate(cls):
        """Check that minimum required credentials are present."""
        required = ["GROQ_API_KEY"]
        missing = [k for k in required if not getattr(cls, k)]
        if missing:
            log_warn = f"⚠️  Missing env vars: {missing}. Some features won't work."
            print(log_warn)
        return len(missing) == 0
