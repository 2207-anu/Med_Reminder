from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from auth import require_admin
from config import GMAIL_PASS, GMAIL_USER
from db_postgres import get_all_patients, log_email
from services.email_service import (
    build_email_html,
    build_schedule_from_db,
    meds_for_timing,
    send_reminder_email,
)

router = APIRouter(prefix="/api/emails", tags=["emails"])


class SendReminderBody(BaseModel):
    patient_email: EmailStr
    timing: str = Field(pattern="^(Morning|Afternoon|Evening|Night)$")
    doctor_name: str = ""
    gmail_user: str = ""
    gmail_pass: str = ""
    medicine_indices: list[int] | None = None


@router.get("/patients")
def patients_with_email(user: dict = Depends(require_admin)):
    patients = get_all_patients(user_id=user["id"])
    with_email = [p for p in patients if p.get("email") and "@" in p.get("email", "")]
    return {"patients": with_email}


@router.get("/schedule/{patient_email}")
def patient_schedule(patient_email: str, user: dict = Depends(require_admin)):
    schedule = build_schedule_from_db(patient_email)
    return {"schedule": schedule}


@router.post("/send")
def send_reminder(body: SendReminderBody, user: dict = Depends(require_admin)):
    gmail_user = body.gmail_user or GMAIL_USER
    gmail_pass = body.gmail_pass or GMAIL_PASS
    if not gmail_user or not gmail_pass:
        raise HTTPException(status_code=400, detail="Gmail credentials missing")

    patients = get_all_patients(user_id=user["id"])
    patient = next(
        (p for p in patients if p.get("email", "").lower() == body.patient_email.lower()),
        None,
    )
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    full_schedule = build_schedule_from_db(body.patient_email)
    timing_meds = meds_for_timing(full_schedule, body.timing)

    if body.medicine_indices is not None:
        pool = timing_meds or full_schedule
        selected = [pool[i] for i in body.medicine_indices if 0 <= i < len(pool)]
    else:
        selected = timing_meds or full_schedule

    if not selected:
        raise HTTPException(status_code=400, detail="No medicines selected for reminder")

    doctor_name = body.doctor_name or user.get("full_name", "Your Doctor")
    doctor_email = user.get("email", "")

    html = build_email_html(
        patient["full_name"],
        selected,
        doctor_name,
        doctor_email,
        body.timing,
    )

    result = send_reminder_email(
        patient["email"],
        f"💊 MedRemind — {body.timing} Medicine Reminder",
        html,
        gmail_user=gmail_user,
        gmail_pass=gmail_pass,
    )

    status = "sent" if result["success"] else f"failed: {result.get('error', 'unknown')}"
    log_email(patient["email"], patient["full_name"], body.timing, status, doctor_email=doctor_email)

    if not result["success"]:
        raise HTTPException(status_code=502, detail=result.get("error", "Send failed"))

    return {"success": True, "message": f"Email sent to {patient['full_name']}"}
