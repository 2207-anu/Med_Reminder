"""Send reminder emails (Gmail settings from config / .env)."""

from __future__ import annotations

import smtplib
from email.mime.text import MIMEText

from config import GMAIL_PASS, GMAIL_USER


def build_body(patient_name: str, medicines: list, timing: str, run_time: str) -> str:
    lines = [
        f"Hello {patient_name},",
        "",
        f"This is your {timing} medicine reminder ({run_time}).",
        "",
        "Medicines to take now:",
    ]
    for i, m in enumerate(medicines, 1):
        lines.append(f"  {i}. {m['name']}")
        lines.append(f"     Dose: {m['dose']}")
        lines.append(f"     Duration: {m['duration']}")
        lines.append(f"     Time: {timing}")
        lines.append("")
    lines.append("— MedRemind")
    return "\n".join(lines)


def send_email(to_email: str, subject: str, body: str) -> None:
    msg = MIMEText(body, "plain")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = to_email
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_PASS)
        server.sendmail(GMAIL_USER, to_email, msg.as_string())
