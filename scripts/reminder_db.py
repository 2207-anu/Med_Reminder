"""PostgreSQL helpers for reminder scripts (connection, logs, active-medicine check)."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta

import psycopg2

from config import DB_CONFIG, DOCTOR_EMAIL

_DURATION_PATTERN = re.compile(
    r"(?P<num>\d+)\s*(?P<unit>day|days|d|week|weeks|wk|w)?",
    re.IGNORECASE,
)
_SKIP_DURATION = frozenset({"", "—", "-", "not specified", "n/a", "na", "none", "unknown"})


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def ensure_email_logs_table() -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS email_logs (
            id            SERIAL PRIMARY KEY,
            patient_email TEXT NOT NULL,
            patient_name  TEXT NOT NULL,
            timing        TEXT NOT NULL,
            status        TEXT NOT NULL,
            doctor_email  TEXT,
            sent_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    cur.close()
    conn.close()


def log_email(patient_email, patient_name, timing, status, doctor_email=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO email_logs "
        "(patient_email, patient_name, timing, status, doctor_email) "
        "VALUES (%s, %s, %s, %s, %s)",
        (
            patient_email,
            patient_name,
            timing,
            status,
            doctor_email if doctor_email is not None else DOCTOR_EMAIL,
        ),
    )
    conn.commit()
    cur.close()
    conn.close()


def has_timing(timing_text, want: str) -> bool:
    if not timing_text:
        return False
    parts = [t.strip() for t in str(timing_text).split(",")]
    return want in parts


def _parse_duration_days(duration_text):
    if duration_text is None:
        return None
    raw = str(duration_text).strip().lower()
    if raw in _SKIP_DURATION:
        return None
    match = _DURATION_PATTERN.search(raw)
    if not match:
        return None
    num = int(match.group("num"))
    if num <= 0:
        return None
    unit = (match.group("unit") or "day").lower()
    return num * 7 if unit in ("week", "weeks", "wk", "w") else num


def is_medicine_active(start_date, duration_days, duration_text) -> bool:
    if start_date is None:
        return False
    if isinstance(start_date, datetime):
        start_date = start_date.date()
    days = duration_days if duration_days is not None else _parse_duration_days(duration_text)
    if days is None:
        return False
    end = start_date + timedelta(days=days - 1)
    today = date.today()
    return start_date <= today <= end
