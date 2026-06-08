import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from PIL import Image

from auth import require_admin
from services.gemini import (
    analyze,
    build_confirmed_meds_from_schedule,
    chat_about_prescription,
    extract_patient_data,
    extract_text,
    is_error,
    parse_schedule,
)

router = APIRouter(prefix="/api/prescriptions", tags=["prescriptions"])


async def _load_image(file: UploadFile) -> Image.Image:
    if file.content_type not in ("image/jpeg", "image/png", "image/jpg"):
        raise HTTPException(status_code=400, detail="Only JPG/PNG images allowed")
    data = await file.read()
    try:
        return Image.open(io.BytesIO(data))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file")


@router.post("/analyze")
async def analyze_prescription(
    file: UploadFile = File(...),
    user: dict = Depends(require_admin),
):
    img = await _load_image(file)
    text = extract_text(img)
    if is_error(text):
        raise HTTPException(status_code=502, detail=text)

    analysis = analyze(text)
    if is_error(analysis):
        return {
            "success": False,
            "extracted": text,
            "error": analysis,
        }

    schedule = parse_schedule(text)
    return {
        "success": True,
        "extracted": text,
        "analysis": analysis,
        "context": text + "\n" + analysis,
        "schedule": schedule or [],
    }


@router.post("/extract-patient")
async def extract_patient_from_prescription(
    file: UploadFile = File(...),
    user: dict = Depends(require_admin),
):
    img = await _load_image(file)
    raw_text = extract_text(img)
    if is_error(raw_text):
        raise HTTPException(status_code=502, detail=raw_text)

    patient_data = extract_patient_data(raw_text)
    schedule = parse_schedule(raw_text)
    confirmed = build_confirmed_meds_from_schedule(schedule)

    return {
        "success": True,
        "patient_data": patient_data,
        "raw_text": raw_text,
        "schedule": schedule,
        "confirmed_meds": confirmed,
    }


class ChatRequest(BaseModel):
    context: str = Field(min_length=1)
    question: str = Field(min_length=1)


@router.post("/chat")
def prescription_chat(body: ChatRequest, user: dict = Depends(require_admin)):
    reply = chat_about_prescription(body.context, body.question)
    return {"reply": reply}
