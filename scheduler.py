"""
scheduler.py — MedRemind Automatic Email Sender (PostgreSQL version)
=====================================================================
Yeh file Windows Task Scheduler se automatically chalti hai.
4 baar daily: Morning(8AM), Afternoon(1PM), Evening(6PM), Night(9PM)
"""

import os
import sys
import smtplib
import argparse
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))
sys.path.insert(0, BASE_DIR)

from db_postgres import get_all_schedules, log_email, init_db

GMAIL_USER  = os.getenv("GMAIL_USER", "")
GMAIL_PASS  = os.getenv("GMAIL_PASS", "")
DOCTOR_NAME = os.getenv("DOCTOR_NAME", "Your Doctor")
DOCTOR_EMAIL = os.getenv("DOCTOR_EMAIL", GMAIL_USER)
VALID_TIMINGS = ("Morning", "Afternoon", "Evening", "Night")


def get_current_timing():
  hour = datetime.now().hour
  if 6 <= hour < 12:
    return "Morning"
  if 12 <= hour < 16:
    return "Afternoon"
  if 16 <= hour < 20:
    return "Evening"
  return "Night"


def parse_timing_arg():
  parser = argparse.ArgumentParser(description="MedRemind automatic medicine reminders")
  parser.add_argument(
    "--timing",
    type=str,
    default=None,
    help="Morning | Afternoon | Evening | Night (cron ke liye recommended)",
  )
  args = parser.parse_args()
  if args.timing:
    label = args.timing.strip().title()
    if label not in VALID_TIMINGS:
      parser.error(f"Invalid timing '{args.timing}'. Use: Morning, Afternoon, Evening, Night")
    return label
  return get_current_timing()


def normalize_times(times):
  if isinstance(times, str):
    return [t.strip() for t in times.split(",") if t.strip()]
  return [t.strip() for t in times] if isinstance(times, (list, tuple)) else []


def med_has_timing(med, timing):
  return timing in normalize_times(med.get("times", []))


def is_valid_patient_email(email):
  e = (email or "").strip().lower()
  return "@" in e and not e.endswith("@medremind.local")

# ── Beautiful HTML Email ──
def build_email_html(patient_name, timing_label, schedule):
    time_icons = {"Morning":"🌅","Afternoon":"☀️","Evening":"🌆","Night":"🌙"}
    icon = time_icons.get(timing_label, "💊")

    schedule_rows = ""
    for med in schedule:
        times = med.get("times", [])
        if isinstance(times, str):
            times = [t.strip() for t in times.split(",")]
        if timing_label in times:
            schedule_rows += f"""
            <tr>
              <td style="padding:12px 16px;border-bottom:1px solid #1e293b;color:#e2e8f0">{med.get('name','—')}</td>
              <td style="padding:12px 16px;border-bottom:1px solid #1e293b;color:#a78bfa">{med.get('dose','—')}</td>
              <td style="padding:12px 16px;border-bottom:1px solid #1e293b;color:#86efac">{med.get('duration','—')}</td>
              <td style="padding:12px 16px;border-bottom:1px solid #1e293b;color:#94a3b8">{med.get('uses') or med.get('instructions','—')}</td>
            </tr>"""

    if not schedule_rows:
        schedule_rows = f'<tr><td colspan="4" style="padding:16px;color:#475569;text-align:center">No medicines for {timing_label}</td></tr>'

    now_str = datetime.now().strftime("%d %b %Y, %I:%M %p")

    return f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#06070d;font-family:'Segoe UI',Arial,sans-serif">
<div style="max-width:620px;margin:0 auto;padding:32px 16px">

  <div style="background:linear-gradient(135deg,#7c3aed,#3b82f6);border-radius:20px;
      padding:32px;margin-bottom:24px;text-align:center">
    <div style="font-size:3rem;margin-bottom:10px">💊</div>
    <div style="font-size:1.6rem;font-weight:700;color:#fff">MedRemind</div>
    <div style="font-size:0.88rem;color:rgba(255,255,255,0.7);margin-top:6px">Automated Medicine Reminder</div>
  </div>

  <div style="background:#0d1117;border:1px solid #1e2d3d;border-radius:16px;padding:24px 28px;margin-bottom:20px">
    <div style="font-size:1.15rem;font-weight:600;color:#f1f5f9;margin-bottom:10px">
      {icon} {timing_label} Medicine Time, {patient_name}!
    </div>
    <div style="font-size:0.88rem;color:#64748b;line-height:1.8">
      It's time to take your <strong style="color:#a78bfa">{timing_label}</strong> medicines.
      Please follow the dosage instructions carefully.
    </div>
  </div>

  <div style="background:#0d1117;border:1px solid #1e2d3d;border-radius:16px;padding:20px;margin-bottom:20px">
    <div style="font-size:0.75rem;font-weight:700;color:#a78bfa;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:16px">
      📋 {timing_label} Medicines
    </div>
    <table style="width:100%;border-collapse:collapse">
      <thead>
        <tr style="background:#1e293b">
          <th style="padding:10px 16px;text-align:left;color:#64748b;font-size:0.75rem">Medicine</th>
          <th style="padding:10px 16px;text-align:left;color:#64748b;font-size:0.75rem">Dose</th>
          <th style="padding:10px 16px;text-align:left;color:#64748b;font-size:0.75rem">Duration</th>
          <th style="padding:10px 16px;text-align:left;color:#64748b;font-size:0.75rem">Instructions</th>
        </tr>
      </thead>
      <tbody>{schedule_rows}</tbody>
    </table>
  </div>

  <div style="background:rgba(34,197,94,0.06);border:1px solid rgba(34,197,94,0.2);border-radius:16px;padding:18px 24px;margin-bottom:20px">
    <div style="font-size:0.8rem;font-weight:700;color:#86efac;margin-bottom:8px">💡 Reminder Tips</div>
    <div style="font-size:0.82rem;color:#64748b;line-height:1.8">
      ✅ Take medicines at the same time every day<br>
      ✅ Do not skip doses<br>
      ✅ If you feel unwell, contact your doctor immediately
    </div>
  </div>

  <div style="text-align:center;padding:16px 0">
    <div style="font-size:0.78rem;color:#334155">
      Sent by <strong style="color:#a78bfa">MedRemind</strong> • Dr. {DOCTOR_NAME} • {now_str}
    </div>
    <div style="font-size:0.72rem;color:#1e293b;margin-top:6px">
      This is an automated reminder. Please do not reply to this email.
    </div>
  </div>

</div>
</body>
</html>"""

# ── Send email ──
def send_email(to_email, patient_name, timing, html_body):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"💊 MedRemind — {timing} Medicine Reminder"
        msg["From"]    = f"MedRemind <{GMAIL_USER}>"
        msg["To"]      = to_email
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASS)
            server.sendmail(GMAIL_USER, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False

# ══════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════
if __name__ == "__main__":
  init_db()

  if not GMAIL_USER or not GMAIL_PASS:
    print("❌ .env mein GMAIL_USER aur GMAIL_PASS add karo!")
    sys.exit(1)

  timing = parse_timing_arg()
  now = datetime.now().strftime("%d %b %Y %I:%M %p")
  print(f"\n{'='*50}")
  print(f"  MedRemind Scheduler — {timing} Run")
  print(f"  Time: {now}")
  print(f"{'='*50}")

  all_schedules = get_all_schedules()

  if not all_schedules:
    print("⚠️  No prescription schedules found.")
    sys.exit(0)

  success = 0
  failed = 0
  skipped = 0

  for entry in all_schedules:
    email = entry["patient_email"]
    name = entry["patient_name"]
    schedule = entry["schedule"]

    if not is_valid_patient_email(email):
      print(f"  ⏭️  {name} — invalid or placeholder email, skipping.")
      skipped += 1
      continue

    if not any(med_has_timing(med, timing) for med in schedule):
      print(f"  ⏭️  {name} — No {timing} medicines, skipping.")
      skipped += 1
      continue

    print(f"  📧 Sending to {name} ({email})...", end=" ")
    html = build_email_html(name, timing, schedule)
    result = send_email(email, name, timing, html)

    if result:
      log_email(email, name, timing, "sent", doctor_email=DOCTOR_EMAIL)
      print("✅ Sent!")
      success += 1
    else:
      log_email(email, name, timing, "failed", doctor_email=DOCTOR_EMAIL)
      failed += 1

  print(f"\n{'='*50}")
  print(f"  ✅ Success: {success} | ❌ Failed: {failed} | ⏭️ Skipped: {skipped}")
  print(f"{'='*50}\n")