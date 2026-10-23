"""Application configuration using pydantic settings."""

import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Locate directories
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)

# Load .env if present in backend or root
for env_path in [os.path.join(BACKEND_DIR, ".env"), os.path.join(PROJECT_ROOT, ".env")]:
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)


class Settings(BaseSettings):
    """App settings loaded from environment variables."""

    # Directories
    UPLOAD_DIR: str = os.path.join(BACKEND_DIR, "uploads")
    OUTPUT_DIR: str = os.path.join(BACKEND_DIR, "output")
    TEMP_DIR: str = os.path.join(BACKEND_DIR, "temp")

    # File limits
    MAX_FILE_SIZE: int = 2048 * 1024 * 1024  # 2GB (2048MB)

    # AI Configuration
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    WHISPER_MODEL: str = "base"

    # Clip settings
    TARGET_CLIP_DURATION_MIN: int = 20
    TARGET_CLIP_DURATION_MAX: int = 40

    # Silence detection
    SILENCE_THRESHOLD: int = -35  # dB
    SILENCE_MIN_DURATION: float = 0.7  # seconds

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()


def get_groq_api_key() -> str:
    """Reload .env dynamically if GROQ_API_KEY was added after startup."""
    if settings.GROQ_API_KEY:
        return settings.GROQ_API_KEY
    for env_path in [os.path.join(BACKEND_DIR, ".env"), os.path.join(PROJECT_ROOT, ".env")]:
        if os.path.exists(env_path):
            load_dotenv(env_path, override=True)
    val = os.environ.get("GROQ_API_KEY", "")
    if val:
        settings.GROQ_API_KEY = val
    return settings.GROQ_API_KEY


def ensure_directories():
    """Create required directories if they don't exist."""
    for dir_path in [settings.UPLOAD_DIR, settings.OUTPUT_DIR, settings.TEMP_DIR]:
        os.makedirs(dir_path, exist_ok=True)
