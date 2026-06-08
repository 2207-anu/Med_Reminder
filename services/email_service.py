import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import GMAIL_PASS, GMAIL_USER
from db_postgres import get_confirmed_medicines, get_schedule_by_email
from services.gemini import normalize_med_times


def build_schedule_from_db(email: str) -> list:
    schedule_entry = get_schedule_by_email(email)
    if schedule_entry:
        if isinstance(schedule_entry, list) and schedule_entry:
            schedule_entry = schedule_entry[0]
        if isinstance(schedule_entry, dict):
            return schedule_entry.get("schedule", []) or []
    confirmed = get_confirmed_medicines(email)
    if confirmed:
        return [{
            "name": med.get("medicine_name") or med.get("name", ""),
            "dose": med.get("dose", ""),
            "duration": med.get("duration", ""),
            "instructions": med.get("uses", ""),
            "times": normalize_med_times(med.get("timing", "")),
        } for med in confirmed]
    return []


def meds_for_timing(schedule: list, timing: str) -> list:
    result = []
    for med in schedule or []:
        times = normalize_med_times(med.get("times", []))
        if timing in times:
            result.append(med)
    return result


def build_email_html(
    patient_name: str,
    schedule: list,
    doctor_name: str,
    doctor_email: str,
    timing_label: str,
) -> str:
    time_icons = {"Morning": "🌅", "Afternoon": "☀️", "Evening": "🌆", "Night": "🌙"}
    icon = time_icons.get(timing_label, "💊")
    schedule_rows = ""
    for med in schedule:
        times = med.get("times", [])
        if isinstance(times, str):
            times = [t.strip() for t in times.split(",")]
        if timing_label in times or not timing_label:
            schedule_rows += f"""
            <tr>
            <td style="padding:10px 14px;border-bottom:1px solid #1e293b;color:#e2e8f0">{med.get('name','—')}</td>
            <td style="padding:10px 14px;border-bottom:1px solid #1e293b;color:#a78bfa">{med.get('dose','—')}</td>
            <td style="padding:10px 14px;border-bottom:1px solid #1e293b;color:#86efac">{med.get('duration','—')}</td>
            <td style="padding:10px 14px;border-bottom:1px solid #1e293b;color:#94a3b8">{med.get('instructions','—')}</td>
            </tr>"""
    if not schedule_rows:
        schedule_rows = (
            f'<tr><td colspan="4" style="padding:10px;color:#475569;text-align:center">'
            f'No medicines for {timing_label}</td></tr>'
        )
    return f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#06070d;font-family:'Segoe UI',sans-serif">
    <div style="max-width:600px;margin:0 auto;padding:32px 16px">
        <div style="background:linear-gradient(135deg,#7c3aed,#3b82f6);border-radius:16px;padding:28px;text-align:center">
        <div style="font-size:2.5rem">💊</div>
        <div style="font-size:1.4rem;font-weight:700;color:#fff">MedRemind</div>
        </div>
        <div style="background:#0d1117;border:1px solid #1e293b;border-radius:14px;padding:24px;margin:20px 0">
        <div style="font-size:1.1rem;font-weight:600;color:#f1f5f9">{icon} {timing_label} Reminder, {patient_name}!</div>
        </div>
        <table style="width:100%;border-collapse:collapse;background:#0d1117">
        <thead><tr style="background:#1e293b">
        <th style="padding:10px;color:#64748b">Medicine</th>
        <th style="padding:10px;color:#64748b">Dose</th>
        <th style="padding:10px;color:#64748b">Duration</th>
        <th style="padding:10px;color:#64748b">Instructions</th>
        </tr></thead>
        <tbody>{schedule_rows}</tbody>
        </table>
        <div style="text-align:center;padding:16px;font-size:0.78rem;color:#334155">
        Dr. {doctor_name} {'• ' + doctor_email if doctor_email else ''} • {datetime.now().strftime('%d %b %Y')}
        </div>
    </div></body></html>"""


def send_reminder_email(
    to_email: str,
    subject: str,
    html_body: str,
    gmail_user: str | None = None,
    gmail_pass: str | None = None,
) -> dict:
    user = gmail_user or GMAIL_USER
    password = gmail_pass or GMAIL_PASS
    if not user or not password:
        return {"success": False, "error": "Gmail credentials missing"}
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(user, password)
            server.sendmail(user, to_email, msg.as_string())
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
