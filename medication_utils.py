"""
Medication schedule helpers — duration parsing and active-period checks.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Optional

# Matches: "5", "5 days", "5 day", "1 week", "2 weeks", "10d"
_DURATION_PATTERN = re.compile(
    r"(?P<num>\d+)\s*(?P<unit>day|days|d|week|weeks|wk|w)?",
    re.IGNORECASE,
)

_SKIP_DURATION = frozenset(
    {"", "—", "-", "not specified", "n/a", "na", "none", "unknown"}
)


def parse_duration_days(duration_text: str | None) -> Optional[int]:
    """
    Parse duration text into number of days.

    Examples:
        "5 days" -> 5
        "1 week" -> 7
        "10" -> 10

    Returns None if duration cannot be parsed (no auto-reminders for that row).
    """
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
    if unit in ("week", "weeks", "wk", "w"):
        return num * 7
    return num


def parse_start_date(value) -> Optional[date]:
    """Accept date, datetime, or DD/MM/YYYY, YYYY-MM-DD strings."""
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()

    text = str(value).strip()
    if not text or text.lower() in _SKIP_DURATION:
        return None

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def compute_end_date(start_date: date, duration_days: int) -> date:
    """end_date = start_date + duration_days (inclusive last day of course)."""
    return start_date + timedelta(days=duration_days - 1)


def is_medicine_active(
    start_date: date | None,
    duration_days: int | None,
    duration_text: str | None = None,
    *,
    reference_date: date | None = None,
) -> bool:
    """
    True if reference_date is within [start_date, end_date] (inclusive).

    If duration_days is missing, tries to parse duration_text.
    If still unknown, returns False (do not send automated reminders).
    """
    today = reference_date or date.today()
    if start_date is None:
        return False

    days = duration_days if duration_days is not None else parse_duration_days(duration_text)
    if days is None:
        return False

    end = compute_end_date(start_date, days)
    return start_date <= today <= end


def format_medicine_period(start_date: date, duration_days: int) -> str:
    end = compute_end_date(start_date, duration_days)
    return f"{start_date.isoformat()} to {end.isoformat()} ({duration_days} days)"
