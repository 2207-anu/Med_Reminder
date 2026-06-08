import io
import json
import re
import time
import threading

from google import genai
from PIL import Image

from config import API_KEYS

ENGLISH_ONLY_RULE = """
LANGUAGE (mandatory):
- The prescription may be handwritten in Hindi, Gujarati, Marathi, Tamil, Telugu, Urdu, Bengali, Punjabi, or any other language.
- Translate ALL text and field values into clear English before you return them.
- Use standard English/generic medicine names when possible.
- Timing must use only these English labels: Morning, Afternoon, Evening, Night.
- Do not return Hindi, regional script, or mixed-language text in the output.
"""

_key_index = 0
_key_lock = threading.Lock()


def _get_client():
    global _key_index
    if not API_KEYS:
        raise RuntimeError("Add GEMINI_API_KEY_1 to your .env file")
    with _key_lock:
        idx = _key_index % len(API_KEYS)
    return genai.Client(api_key=API_KEYS[idx])


def _switch_key():
    global _key_index
    with _key_lock:
        _key_index = (_key_index + 1) % len(API_KEYS)


def is_error(text: str) -> bool:
    return text.startswith("❌") or text.startswith("⚠️")


def gemini_call(contents) -> str:
    for attempt in range(6):
        client = _get_client()
        try:
            res = client.models.generate_content(model="gemini-2.5-flash", contents=contents)
            if res:
                if hasattr(res, "text") and res.text:
                    return res.text.strip()
                if hasattr(res, "candidates"):
                    try:
                        return res.candidates[0].content.parts[0].text.strip()
                    except Exception:
                        pass
            return "⚠️ Empty response"
        except Exception as e:
            err = str(e)
            if "429" in err:
                _switch_key()
                time.sleep(2 ** attempt)
                continue
            if any(x in err for x in ["503", "500", "disconnected", "timeout", "reset"]):
                time.sleep(3 * (attempt + 1))
                continue
            return f"❌ Error: {err}"
    return "❌ Server busy — please retry."


def image_to_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    if max(img.size) > 1600:
        img = img.copy()
        img.thumbnail((1600, 1600), Image.LANCZOS)
    rgb_img = img.convert("RGB")
    rgb_img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def extract_text(img: Image.Image) -> str:
    return gemini_call([{"role": "user", "parts": [
        {"text": f"""Look at this prescription image carefully.
        Extract ONLY the handwritten text — text written by hand with a pen.
        DO NOT extract any printed, typed, or pre-printed text (like hospital name, letterhead, doctor stamp, clinic address, printed labels).
        Only return what is handwritten on the prescription.

        {ENGLISH_ONLY_RULE}
        Return the handwritten content translated into English (one readable block of text)."""},
        {"inline_data": {"mime_type": "image/jpeg", "data": image_to_bytes(img)}},
    ]}])


def analyze(text: str) -> str:
    return gemini_call(f"""Analyze this prescription: {text}

    {ENGLISH_ONLY_RULE}
    Reply in simple English only. Bullet points.
    Format:
    1. Medicine: <name>
    Use: <meaning>
    Duration: <days>
    How to take: <instruction>""")


def parse_schedule(text: str) -> list:
    raw = gemini_call(f"""From this prescription, extract ONLY the medicine schedule.
Prescription text: {text}

{ENGLISH_ONLY_RULE}

IMPORTANT:
- Extract exactly what the prescription says, but write every value in English
- For each medicine, list: name, dose, times (Morning/Afternoon/Evening/Night), duration, uses
- Uses = what is the medicine used/prescribed for (medical purpose only), in simple English
- Uses must be BRIEF (max 2 lines/15 words): e.g. "Treats type 2 diabetes" or "Pain relief and fever reduction"
- If information is unclear or missing, use "Not specified"
- Return ONLY valid JSON array, no markdown, no extra text

Example format:
[{{"name":"Aspirin","dose":"500mg","times":"Morning","duration":"5 days","uses":"Pain relief"}},...]

Prescription medicines:""")
    raw = re.sub(r"```(?:json)?", "", raw.strip()).strip("` \n")
    try:
        data = json.loads(raw)
        for item in data:
            if "instructions" in item and "uses" not in item:
                item["uses"] = item.pop("instructions")
        return data
    except Exception:
        return []


def normalize_med_times(times) -> list:
    if isinstance(times, str):
        return [t.strip() for t in times.split(",") if t.strip()]
    return list(times) if times else []


def fetch_med_uses(name: str, existing: str = "") -> str:
    if existing and existing not in ["—", "Not specified", ""]:
        return existing
    uses = gemini_call(f"""What is {name} medicine used for?
{ENGLISH_ONLY_RULE}
Answer in ONE simple English sentence only (max 15 words).
No extra text, no bullet points.""")
    return uses.strip() if uses and not is_error(uses) else ""


def schedule_to_confirmed_med(med: dict) -> dict:
    times = normalize_med_times(med.get("times", []))
    dur = med.get("duration", "")
    if dur in ["—", "Not specified"]:
        dur = ""
    return {
        "name": med.get("name", ""),
        "dose": med.get("dose", ""),
        "duration": dur,
        "times": times,
        "uses": fetch_med_uses(med.get("name", ""), med.get("uses", "")),
    }


def build_confirmed_meds_from_schedule(schedule: list) -> list:
    return [schedule_to_confirmed_med(m) for m in schedule if m.get("name")]


def extract_patient_data(raw_text: str) -> dict:
    prompt = f"""
    This is handwritten text from a prescription (printed text has already been removed):
    {raw_text}

    Extract patient details from ONLY this handwritten content.
    Ignore anything that looks like hospital name, clinic address, doctor stamp, or pre-printed letterhead.

    {ENGLISH_ONLY_RULE}
    Every JSON string value must be in English.

    Return ONLY a valid JSON object. No explanation, no markdown.
    Fields:
    {{
      "full_name": "",
      "age": "",
      "gender": "",
      "phone": "",
      "email": "",
      "disease": "",
      "medicines": "",
      "prescription_date": "",
      "doctor_notes": ""
    }}
    If any field not found, use empty string.
    """
    raw = gemini_call(prompt)
    raw = re.sub(r"```(?:json)?", "", raw.strip()).strip("` \n")
    try:
        return json.loads(raw)
    except Exception:
        return {}


def chat_about_prescription(context: str, question: str) -> str:
    reply = gemini_call(
        f"Medical assistant. Answer based on context only.\n"
        f"{ENGLISH_ONLY_RULE}\n"
        f"Context: {context}\n"
        f"Question: {question}\n"
        f"Reply in simple English only, concise."
    )
    if is_error(reply):
        return "⚠️ Server busy. Please try again in a moment."
    return reply
