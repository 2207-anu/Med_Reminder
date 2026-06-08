"""
Evening reminder — 6:00 PM
  python scripts/evening_6pm.py

Cron: python scripts/setup_windows_tasks.py  →  MedRemind-Evening-6PM
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import require_mail_config
from reminder_db import (
    ensure_email_logs_table,
    get_connection,
    has_timing,
    is_medicine_active,
    log_email,
)
from reminder_mail import build_body, send_email

TIMING = "Evening"
RUN_TIME = "6:00 PM"


def get_evening_patients():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT patient_email, patient_name, medicine_name, dose, duration, timing,
               start_date, duration_days
        FROM confirmed_medicines
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    patients = {}
    for email, name, med_name, dose, duration, timing, start_date, duration_days in rows:
        if not has_timing(timing, TIMING):
            continue
        if not is_medicine_active(start_date, duration_days, duration):
            continue
        email = (email or "").strip().lower()
        if "@" not in email or email.endswith("@medremind.local"):
            continue
        if email not in patients:
            patients[email] = {"name": name, "email": email, "medicines": []}
        patients[email]["medicines"].append({
            "name": med_name,
            "dose": dose or "-",
            "duration": duration or "-",
        })
    return list(patients.values())


def main():
    require_mail_config()
    ensure_email_logs_table()
    print(f"\n=== {TIMING} reminder ({RUN_TIME}) ===\n")

    patients = get_evening_patients()
    if not patients:
        print(f"No patients with {TIMING} medicines.")
        return 0

    sent = 0
    subject = f"MedRemind - {TIMING} medicine reminder"
    for p in patients:
        print(f"Patient: {p['name']} | {p['email']}")
        for m in p["medicines"]:
            print(f"  - {m['name']} | {m['dose']} | {TIMING}")
        try:
            send_email(p["email"], subject, build_body(p["name"], p["medicines"], TIMING, RUN_TIME))
            log_email(p["email"], p["name"], TIMING, "sent")
            print("  Email sent OK\n")
            sent += 1
        except Exception as e:
            log_email(p["email"], p["name"], TIMING, f"failed: {e}")
            print(f"  Email failed: {e}\n")

    print(f"Done. Sent: {sent}/{len(patients)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
