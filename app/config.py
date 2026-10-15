"""Cedar Lane Auto Detailing — app configuration."""

import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


class Settings:  # pylint: disable=too-few-public-methods
    """Flat settings bag loaded from environment variables."""

    PROJECT_NAME = "Cedar Lane Auto Detailing - AI Receptionist"
    VERSION = "1.0.0"

    SHOP_NAME = os.getenv("SHOP_NAME", "Cedar Lane Auto Detailing")
    SHOP_PHONE = os.getenv("SHOP_PHONE", "(415) 555-0142")
    SHOP_TIMEZONE = os.getenv("SHOP_TIMEZONE", "America/Los_Angeles")

    OPEN_HOUR = int(os.getenv("OPEN_HOUR", "8"))
    CLOSE_HOUR = int(os.getenv("CLOSE_HOUR", "18"))

    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    SERVICE_ACCOUNT_FILE = os.getenv(
        "GOOGLE_SERVICE_ACCOUNT_PATH", str(ROOT_DIR / "service_account.json")
    )
    GOOGLE_CALENDAR_ID = os.getenv(
        "GOOGLE_CALENDAR_ID",
        "545554d58631fde9dfc44723a1e860e0f49970ac99055e66992666a0ddeb478f@group.calendar.google.com",
    )
    GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
    CONTACTS_FILE: Path = ROOT_DIR / "data" / "contacts.json"
    CONTACTS_CSV: Path = ROOT_DIR / "data" / "contacts.csv"

    VAPI_API_KEY = os.getenv("VAPI_API_KEY", "")
    VAPI_ASSISTANT_ID = os.getenv("VAPI_ASSISTANT_ID", "")
    SERVER_PUBLIC_URL = os.getenv("SERVER_PUBLIC_URL", "")


settings = Settings()
