"""Session state, Gemini, patient helpers."""
import os
import io
import time
import re
import json
import textwrap
import streamlit as st
from google import genai
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

API_KEYS = [
    os.getenv("GEMINI_API_KEY_1"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3"),
]
API_KEYS = [k for k in API_KEYS if k]

GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_PASS = os.getenv("GMAIL_PASS", "")

def check_gemini_keys():
    if not API_KEYS:
        st.error("❌ Add GEMINI_API_KEY_1 to your .env file.")
        st.stop()

# ══════════════════════════════════════════
#  SESSION STATE
# ══════════════════════════════════════════
def valid_email(e): return re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', e)

def init_session():
    for k, v in {
        "admin_logged_in": False,
        "admin_user": None,
        "admin_auth_tab": "login",
        "admin_nav": "Dashboard",
        "key_index": 0,
        "chat": [],
        "rx_page": "Upload",
        "reminders": {},
        "schedule": [],
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v


def get_current_user_id():
    user = st.session_state.get("admin_user")
    return user.get("id") if user else None


def clear_user_workspace():
    """Reset prescription/patient UI state when switching accounts."""
    for key in list(st.session_state.keys()):
        if key.startswith("pr_") or key in (
            "extracted", "analysis", "context", "schedule", "reminders", "chat",
        ):
            del st.session_state[key]


def user_initials(user: dict) -> str:
    name = (user or {}).get("full_name", "").strip()
    if name:
        parts = name.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return name[0].upper()
    email = (user or {}).get("email", "")
    return email[0].upper() if email else "?"


def render_profile_header(user: dict):
    """Top bar with logged-in email and profile chip (website-style)."""
    initials = user_initials(user)
    full_name = user.get("full_name") or "Doctor"
    email = user.get("email") or ""
    st.markdown(f"""
    <div class="app-topbar">
        <div class="app-topbar-left">
            <div class="app-brand">💊 Med<span>Remind</span></div>
        </div>
        <div class="profile-menu">
            <div class="profile-avatar">{initials}</div>
            <div class="profile-info">
                <div class="profile-role">Signed in</div>
                <div class="profile-name">{full_name}</div>
                <div class="profile-email">{email}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════
#  GEMINI HELPERS
# ══════════════════════════════════════════
def get_client(): return genai.Client(api_key=API_KEYS[st.session_state.key_index])
def switch_key(): st.session_state.key_index = (st.session_state.key_index + 1) % len(API_KEYS)

# Applied to every Gemini extraction prompt — any input language → English output
ENGLISH_ONLY_RULE = """
LANGUAGE (mandatory):
- The prescription may be handwritten in Hindi, Gujarati, Marathi, Tamil, Telugu, Urdu, Bengali, Punjabi, or any other language.
- Translate ALL text and field values into clear English before you return them.
- Use standard English/generic medicine names when possible.
- Timing must use only these English labels: Morning, Afternoon, Evening, Night.
- Do not return Hindi, regional script, or mixed-language text in the output.
"""

def gemini_call(contents):
    client = get_client()
    for attempt in range(6):
        try:
            res = client.models.generate_content(model="gemini-2.5-flash", contents=contents)
            if res:
                if hasattr(res, "text") and res.text:
                    return res.text.strip()
                if hasattr(res, "candidates"):
                    try:
                        return res.candidates[0].content.parts[0].text.strip()
                    except:
                        pass
            return "⚠️ Empty response"
        except Exception as e:
            err = str(e)
            if "429" in err:
                switch_key(); client = get_client()
                time.sleep(2 ** attempt); continue
            if any(x in err for x in ["503", "500", "disconnected", "timeout", "reset"]):
                time.sleep(3 * (attempt + 1)); continue
            return f"❌ Error: {err}"
    return "❌ Server busy — please retry."


def image_to_bytes(img):
    buf = io.BytesIO()
    if max(img.size) > 1600:
        img = img.copy()
        img.thumbnail((1600, 1600), Image.LANCZOS)
    rgb_img = img.convert("RGB")
    rgb_img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def extract_text(img):
    return gemini_call([{"role": "user", "parts": [
        {"text": f"""Look at this prescription image carefully.
        Extract ONLY the handwritten text — text written by hand with a pen.
        DO NOT extract any printed, typed, or pre-printed text (like hospital name, letterhead, doctor stamp, clinic address, printed labels).
        Only return what is handwritten on the prescription.

        {ENGLISH_ONLY_RULE}
        Return the handwritten content translated into English (one readable block of text)."""},
        {"inline_data": {"mime_type": "image/jpeg", "data": image_to_bytes(img)}}
    ]}])


def analyze(text):
    return gemini_call(f"""Analyze this prescription: {text}

    {ENGLISH_ONLY_RULE}
    Reply in simple English only. Bullet points.
    Format:
    1. Medicine: <name>
    Use: <meaning>
    Duration: <days>
    How to take: <instruction>""")


def parse_schedule(text):
    raw = gemini_call(f"""From this prescription, extract ONLY the medicine schedule.
Prescription text: {text}

{ENGLISH_ONLY_RULE}

IMPORTANT:
- Extract exactly what the prescription says, but write every value in English.
- For each medicine, return fields: name, dose, times (Morning/Afternoon/Evening/Night), duration, instructions, uses, uses_explanation.
- instructions = how to take the medicine in one short phrase.
- uses = what the medicine is prescribed for, in simple English.
- uses_explanation = two short sentences in normal English explaining why this medicine is used.
- If information is unclear or missing, use "Not specified".
- Return ONLY a valid JSON array, no markdown, no extra text.

Example format:
[{{"name":"Aspirin","dose":"500mg","times":"Morning","duration":"5 days","instructions":"Take one tablet in the Morning","uses":"Pain relief","uses_explanation":"Aspirin is used to relieve pain and lower fever. It helps reduce inflammation and ease mild to moderate pain."}},...]

Prescription medicines:""")
    raw = re.sub(r"```(?:json)?", "", raw.strip()).strip("` \n")
    try:
        data = json.loads(raw)
        for item in data:
            if "instructions" in item and "uses" not in item:
                item["uses"] = item.pop("instructions")
        return data
    except Exception as e:
        print(f"Parse error: {e}")
        return []


def schedule_to_table_rows(schedule):
    rows = []
    for idx, med in enumerate(schedule, start=1):
        times = med.get("times", [])
        if isinstance(times, list):
            times = ", ".join(times)
        times = times or "Not specified"
        instructions = med.get("instructions", med.get("how_to_take", "Not specified")) or "Not specified"
        uses = med.get("uses", "Not specified") or "Not specified"
        uses_explanation = med.get("uses_explanation", "") or "Not specified"
        uses_explanation = uses_explanation.replace("\n", " ")
        rows.append({
            "#": idx,
            "Medicine": med.get("name", "Unknown"),
            "Dose": med.get("dose", "—"),
            "Times": times,
            "Duration": med.get("duration", "—"),
            "How to take": instructions,
            "Uses": uses,
            "Uses explanation": uses_explanation,
        })
    return rows


def schedule_to_html_table(schedule):
    if not schedule:
        return ""
    rows = []
    for idx, med in enumerate(schedule, start=1):
        times = med.get("times", [])
        if isinstance(times, list):
            times = ", ".join(times)
        times = times or "Not specified"
        instructions = med.get("instructions", med.get("how_to_take", "Not specified")) or "Not specified"
        uses = med.get("uses", "Not specified") or "Not specified"
        uses_explanation = med.get("uses_explanation", "") or "Not specified"
        uses_explanation = uses_explanation.replace("\n", " ")
        rows.append(textwrap.dedent(f"""
            <tr>
                <td style=\"padding:12px 10px;border-top:1px solid rgba(148,163,184,0.15);font-weight:700;\">{idx}</td>
                <td style=\"padding:12px 10px;border-top:1px solid rgba(148,163,184,0.15);\">{med.get('name','Unknown')}</td>
                <td style=\"padding:12px 10px;border-top:1px solid rgba(148,163,184,0.15);\">{med.get('dose','—')}</td>
                <td style=\"padding:12px 10px;border-top:1px solid rgba(148,163,184,0.15);\">{times}</td>
                <td style=\"padding:12px 10px;border-top:1px solid rgba(148,163,184,0.15);\">{med.get('duration','—')}</td>
                <td style=\"padding:12px 10px;border-top:1px solid rgba(148,163,184,0.15);\">{instructions}</td>
                <td style=\"padding:12px 10px;border-top:1px solid rgba(148,163,184,0.15);\">{uses}</td>
                <td style=\"padding:12px 10px;border-top:1px solid rgba(148,163,184,0.15);font-size:0.92rem;color:#cbd5e1;line-height:1.45;\">{uses_explanation}</td>
            </tr>
        """))
    return textwrap.dedent(f"""
<div class=\"glass-card\" style=\"overflow-x:auto;padding:0.5rem 0;\">
<table style=\"width:100%;border-collapse:collapse;color:#e2e8f0;min-width:860px;\">
    <thead>
    <tr style=\"text-align:left;color:#a78bfa;font-size:0.92rem;\">
        <th style=\"padding:12px 10px;border-bottom:1px solid rgba(148,163,184,0.25);\">#</th>
        <th style=\"padding:12px 10px;border-bottom:1px solid rgba(148,163,184,0.25);\">Medicine</th>
        <th style=\"padding:12px 10px;border-bottom:1px solid rgba(148,163,184,0.25);\">Dose</th>
        <th style=\"padding:12px 10px;border-bottom:1px solid rgba(148,163,184,0.25);\">Times</th>
        <th style=\"padding:12px 10px;border-bottom:1px solid rgba(148,163,184,0.25);\">Duration</th>
        <th style=\"padding:12px 10px;border-bottom:1px solid rgba(148,163,184,0.25);\">How to take</th>
        <th style=\"padding:12px 10px;border-bottom:1px solid rgba(148,163,184,0.25);\">Uses</th>
        <th style=\"padding:12px 10px;border-bottom:1px solid rgba(148,163,184,0.25);\">Uses explanation</th>
    </tr>
    </thead>
    <tbody>{''.join(rows)}</tbody>
</table>
</div>
""")


def is_error(text):
    return text.startswith("❌") or text.startswith("⚠️")


def normalize_med_times(times):
    if isinstance(times, str):
        return [t.strip() for t in times.split(",") if t.strip()]
    return list(times) if times else []


def fetch_med_uses(name, existing=""):
    if existing and existing not in ["—", "Not specified", ""]:
        return existing
    uses = gemini_call(f"""What is {name} medicine used for?
{ENGLISH_ONLY_RULE}
Answer in ONE simple English sentence only (max 15 words).
No extra text, no bullet points.
Examples: 
- "Treats type 2 diabetes"
- "Pain relief and fever reduction"
- "Treats bacterial infections"
""")
    return uses.strip() if uses and not is_error(uses) else ""


def schedule_to_confirmed_med(med):
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


def build_confirmed_meds_from_schedule(schedule):
    return [schedule_to_confirmed_med(m) for m in schedule if m.get("name")]


def sync_med_edits_from_widgets():
    meds = st.session_state.pr_confirmed_meds
    for idx in range(len(meds)):
        for field, prefix in [("name", "pr_med_name"), ("dose", "pr_med_dose"),
                            ("uses", "pr_med_uses"), ("duration", "pr_med_dur")]:
            key = f"{prefix}_{idx}"
            if key in st.session_state:
                meds[idx][field] = st.session_state[key]


def sync_patient_form_session(fname, age, gender, phone, email, date, disease, notes):
    """Keep verify form + medicines section visible after save."""
    st.session_state.pr_extracted_data = {
        "full_name": fname.strip(),
        "age": age,
        "gender": gender if gender != "Select" else "",
        "phone": phone,
        "email": email,
        "disease": disease,
        "prescription_date": date,
        "doctor_notes": notes,
    }


def read_patient_form_values():
    """Read verify form; works even when save is clicked from medicines section."""
    d = st.session_state.get("pr_extracted_data") or {}
    return {
        "fname":   st.session_state.get("prf_name",    d.get("full_name", "")),
        "age":     st.session_state.get("prf_age",     d.get("age", "")),
        "gender":  st.session_state.get("prf_gender",  d.get("gender", "")),
        "phone":   st.session_state.get("prf_phone",   d.get("phone", "")),
        "email":   st.session_state.get("prf_email",   d.get("email", "")),
        "date":    st.session_state.get("prf_date",    d.get("prescription_date", "")),
        "disease": st.session_state.get("prf_disease", d.get("disease", "")),
        "notes":   st.session_state.get("prf_notes",   d.get("doctor_notes", "")),
    }


def persist_patient_record():
    """Save/update one patient row; reuse pr_saved_patient_id to avoid duplicates."""
    from db_postgres import add_patient, update_patient

    v = read_patient_form_values()
    if not v["fname"].strip():
        return {"success": False, "message": "Patient Full Name is required!"}

    user_id = get_current_user_id()
    if not user_id:
        return {"success": False, "message": "You must be logged in to save patients."}

    admin = st.session_state.get("admin_user") or {}
    doctor_email = (admin.get("email") or "").strip().lower() or None

    existing_id = st.session_state.get("pr_saved_patient_id")

    if not existing_id and v["email"] and v["email"].strip():
        from db_postgres import get_patient_by_email

        existing = get_patient_by_email(v["email"])
        if existing:
            owner = existing.get("user_id")
            if owner is None or owner == user_id:
                existing_id = existing["id"]

    if existing_id:
        result = update_patient(
            patient_id=existing_id,
            full_name=v["fname"].strip(),
            age=v["age"],
            gender=v["gender"] if v["gender"] != "Select" else "",
            phone=v["phone"],
            email=v["email"].lower().strip() if v["email"] else "",
            disease=v["disease"],
            doctor_notes=v["notes"],
            prescription_date=v["date"],
            added_by="admin",
            user_id=user_id,
            added_by_email=doctor_email,
        )
    else:
        result = add_patient(
            full_name=v["fname"].strip(),
            age=v["age"],
            gender=v["gender"] if v["gender"] != "Select" else "",
            phone=v["phone"],
            email=v["email"].lower().strip() if v["email"] else "",
            disease=v["disease"],
            doctor_notes=v["notes"],
            prescription_date=v["date"],
            added_by="admin",
            user_id=user_id,
            added_by_email=doctor_email,
        )

    if result.get("success"):
        sync_patient_form_session(
            v["fname"], v["age"], v["gender"], v["phone"],
            v["email"], v["date"], v["disease"], v["notes"],
        )
        st.session_state.pr_saved_patient_id = result["patient_id"]
    return result
