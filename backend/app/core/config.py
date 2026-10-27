
"""Application configuration anchored to the backend directory."""

import os
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_DIR / ".env")

GEMMA_API_KEY = os.getenv("GEMINI_API_KEY")
GEMMA_MODEL = os.getenv("GEMMA_MODEL", "gemma-4-26b-a4b-it")
GEMINI_VISION_MODEL = os.getenv("GEMINI_VISION_MODEL", "gemini-3.8-flash").strip()
DATABASE_URL = os.getenv("DATABASE_URL")
AI_REQUEST_TIMEOUT_SECONDS = int(os.getenv("AI_REQUEST_TIMEOUT_SECONDS", "30"))
_upload_dir_setting = Path(os.getenv("UPLOAD_DIR", "uploads"))
UPLOAD_DIR = (_upload_dir_setting if _upload_dir_setting.is_absolute() else BACKEND_DIR / _upload_dir_setting).resolve()
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))


def validate_database_configuration() -> None:
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is missing. Configure it in backend/.env.")
