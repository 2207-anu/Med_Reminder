from fastapi import APIRouter, Depends

from auth import require_admin
from db_postgres import get_all_patients, get_all_schedules, get_email_logs

router = APIRouter(prefix="/api/activity", tags=["activity"])


@router.get("")
def activity_summary(user: dict = Depends(require_admin)):
    user_id = user["id"]
    doctor_email = user.get("email", "")
    return {
        "patients": get_all_patients(user_id=user_id),
        "schedules": get_all_schedules(user_id=user_id),
        "email_logs": get_email_logs(50, doctor_email=doctor_email),
    }
