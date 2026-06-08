"""Load all settings from project .env (no secrets in script files)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / ".env")

GMAIL_USER = os.getenv("GMAIL_USER", "").strip()
GMAIL_PASS = os.getenv("GMAIL_PASS", "").strip()
DOCTOR_EMAIL = os.getenv("DOCTOR_EMAIL", GMAIL_USER).strip()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "medicine_app"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}


def require_mail_config() -> None:
    if not GMAIL_USER or not GMAIL_PASS:
        raise SystemExit("Error: set GMAIL_USER and GMAIL_PASS in .env")
