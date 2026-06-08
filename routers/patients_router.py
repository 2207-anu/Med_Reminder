from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from auth import require_admin
from db_postgres import (
    add_patient,
    delete_patient,
    get_all_patients,
    get_confirmed_medicines_by_id,
    get_patient_by_email,
    save_confirmed_medicines,
    save_prescription_schedule,
    update_patient,
)

router = APIRouter(prefix="/api/patients", tags=["patients"])


class PatientBody(BaseModel):
    full_name: str = Field(min_length=1)
    age: str = ""
    gender: str = ""
    phone: str = ""
    email: str = ""
    disease: str = ""
    doctor_notes: str = ""
    prescription_date: str = ""


class MedicineItem(BaseModel):
    name: str
    dose: str = ""
    uses: str = ""
    instructions: str = ""
    times: list[str] = []
    duration: str = ""


class SaveMedicinesBody(BaseModel):
    patient: PatientBody
    medicines: list[MedicineItem]
    extracted_text: str = ""
    patient_id: int | None = None


@router.get("")
def list_patients(user: dict = Depends(require_admin)):
    return {"patients": get_all_patients(user_id=user["id"])}


@router.get("/{patient_id}")
def get_patient(patient_id: int, user: dict = Depends(require_admin)):
    patients = get_all_patients(user_id=user["id"])
    match = next((p for p in patients if p["id"] == patient_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Patient not found")
    medicines = get_confirmed_medicines_by_id(patient_id)
    return {"patient": match, "medicines": medicines}


@router.post("")
def create_patient(body: PatientBody, user: dict = Depends(require_admin)):
    doctor_email = user.get("email", "").strip().lower() or None

    if body.email and body.email.strip():
        existing = get_patient_by_email(body.email)
        if existing and existing.get("user_id") not in (None, user["id"]):
            raise HTTPException(status_code=409, detail="Patient email registered under another doctor")
        if existing and existing.get("user_id") in (None, user["id"]):
            result = update_patient(
                patient_id=existing["id"],
                full_name=body.full_name.strip(),
                age=body.age,
                gender=body.gender if body.gender != "Select" else "",
                phone=body.phone,
                email=body.email.lower().strip(),
                disease=body.disease,
                doctor_notes=body.doctor_notes,
                prescription_date=body.prescription_date,
                user_id=user["id"],
                added_by_email=doctor_email,
            )
        else:
            result = add_patient(
                full_name=body.full_name.strip(),
                age=body.age,
                gender=body.gender if body.gender != "Select" else "",
                phone=body.phone,
                email=body.email.lower().strip() if body.email else "",
                disease=body.disease,
                doctor_notes=body.doctor_notes,
                prescription_date=body.prescription_date,
                user_id=user["id"],
                added_by_email=doctor_email,
            )
    else:
        result = add_patient(
            full_name=body.full_name.strip(),
            age=body.age,
            gender=body.gender if body.gender != "Select" else "",
            phone=body.phone,
            email=body.email.lower().strip() if body.email else "",
            disease=body.disease,
            doctor_notes=body.doctor_notes,
            prescription_date=body.prescription_date,
            user_id=user["id"],
            added_by_email=doctor_email,
        )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Save failed"))
    return result


class PatientUpdateBody(PatientBody):
    patient_id: int | None = None


@router.put("/{patient_id}")
def update_patient_route(patient_id: int, body: PatientBody, user: dict = Depends(require_admin)):
    doctor_email = user.get("email", "").strip().lower() or None
    result = update_patient(
        patient_id=patient_id,
        full_name=body.full_name.strip(),
        age=body.age,
        gender=body.gender if body.gender != "Select" else "",
        phone=body.phone,
        email=body.email.lower().strip() if body.email else "",
        disease=body.disease,
        doctor_notes=body.doctor_notes,
        prescription_date=body.prescription_date,
        user_id=user["id"],
        added_by_email=doctor_email,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Update failed"))
    return result


@router.delete("/{patient_id}")
def remove_patient(patient_id: int, user: dict = Depends(require_admin)):
    result = delete_patient(patient_id, user_id=user["id"])
    if not result.get("success"):
        raise HTTPException(status_code=404, detail="Patient not found or access denied")
    return {"success": True}


@router.post("/save-with-medicines")
def save_with_medicines(body: SaveMedicinesBody, user: dict = Depends(require_admin)):
    if not body.medicines:
        raise HTTPException(status_code=400, detail="Add at least one medicine")

    doctor_email = user.get("email", "").strip().lower() or None
    patient_id = body.patient_id

    if patient_id:
        result = update_patient(
            patient_id=patient_id,
            full_name=body.patient.full_name.strip(),
            age=body.patient.age,
            gender=body.patient.gender if body.patient.gender != "Select" else "",
            phone=body.patient.phone,
            email=body.patient.email.lower().strip() if body.patient.email else "",
            disease=body.patient.disease,
            doctor_notes=body.patient.doctor_notes,
            prescription_date=body.patient.prescription_date,
            user_id=user["id"],
            added_by_email=doctor_email,
        )
    else:
        result = add_patient(
            full_name=body.patient.full_name.strip(),
            age=body.patient.age,
            gender=body.patient.gender if body.patient.gender != "Select" else "",
            phone=body.patient.phone,
            email=body.patient.email.lower().strip() if body.patient.email else "",
            disease=body.patient.disease,
            doctor_notes=body.patient.doctor_notes,
            prescription_date=body.patient.prescription_date,
            user_id=user["id"],
            added_by_email=doctor_email,
        )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Patient save failed"))

    patient_id = result["patient_id"]
    email_clean = body.patient.email.lower().strip() if body.patient.email else ""
    storage_email = email_clean or f"patient_{patient_id}@medremind.local"
    meds_list = [m.model_dump() for m in body.medicines]

    sched_result = save_prescription_schedule(
        patient_id=patient_id,
        patient_email=storage_email,
        patient_name=body.patient.full_name.strip(),
        schedule_list=meds_list,
        extracted_text=body.extracted_text,
    )
    meds_result = save_confirmed_medicines(
        patient_id=patient_id,
        patient_email=storage_email,
        patient_name=body.patient.full_name.strip(),
        medicines_list=meds_list,
    )

    if not sched_result.get("success"):
        raise HTTPException(status_code=400, detail=sched_result.get("message", "Schedule save failed"))
    if not meds_result.get("success"):
        raise HTTPException(status_code=400, detail=meds_result.get("message", "Medicines save failed"))

    return {
        "success": True,
        "patient_id": patient_id,
        "medicines_saved": len(meds_list),
    }
