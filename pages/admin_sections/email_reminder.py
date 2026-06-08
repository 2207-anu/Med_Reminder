"""Admin section: Email Reminder."""
import streamlit as st

import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from db_postgres import log_email
from pages.admin_sections.shared import GMAIL_USER, GMAIL_PASS, get_current_user_id

def render(user):
    from db_postgres import get_all_patients, get_schedule_by_email, get_confirmed_medicines

    st.markdown('<div class="sec-title">📧 Email Reminder</div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-sub">Send medicine reminders to patients via Gmail.</div>', unsafe_allow_html=True)

    doctor_email = st.session_state.admin_user.get("email", "") if st.session_state.admin_user else ""
    doctor_name = st.session_state.admin_user.get("full_name", "Your Doctor") if st.session_state.admin_user else "Your Doctor"

    gmail_user = GMAIL_USER or st.session_state.get("gmail_user_override", "")
    gmail_pass = GMAIL_PASS or st.session_state.get("gmail_pass_override", "")

    def normalize_times(times):
        if isinstance(times, str):
            return [t.strip() for t in times.split(",") if t.strip()]
        return [t.strip() for t in times] if isinstance(times, (list, tuple)) else []

    def build_schedule_from_db(email):
        schedule_entry = get_schedule_by_email(email)
        if schedule_entry:
            if isinstance(schedule_entry, list) and schedule_entry:
                schedule_entry = schedule_entry[0]
            if isinstance(schedule_entry, dict):
                return schedule_entry.get("schedule", []) or []
        confirmed = get_confirmed_medicines(email)
        if confirmed:
            normalized = []
            for med in confirmed:
                normalized.append({
                    "name": med.get("medicine_name") or med.get("name", ""),
                    "dose": med.get("dose", ""),
                    "duration": med.get("duration", ""),
                    "instructions": med.get("uses", ""),
                    "times": normalize_times(med.get("timing", "")),
                })
            return normalized
        return []

    def meds_for_timing(schedule, timing):
        if not schedule:
            return []
        result = []
        for med in schedule:
            times = normalize_times(med.get("times", []))
            if timing in times:
                result.append(med)
        return result

    if not gmail_user or not gmail_pass:
        st.markdown("""
        <div style="background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.4);border-radius:14px;padding:18px;margin-bottom:18px">
        <div style="font-family:'Syne',sans-serif;font-weight:700;color:#fca5a5;margin-bottom:8px">
            ⚠️ Gmail Setup Required
        </div>
        <div style="font-size:0.85rem;color:#94a3b8;line-height:1.8">
            Add <code style="background:#0d1117;padding:2px 8px;border-radius:4px;color:#86efac">GMAIL_USER</code>
            and <code style="background:#0d1117;padding:2px 8px;border-radius:4px;color:#86efac">GMAIL_PASS</code>
            in your <code>.env</code> file, or enter them below (Gmail App Password).
        </div>
        </div>""", unsafe_allow_html=True)
        with st.expander("Gmail credentials (this session)", expanded=True):
            st.session_state.gmail_user_override = st.text_input(
                "Gmail address", value=st.session_state.get("gmail_user_override", ""), key="gmail_user_in"
            )
            st.session_state.gmail_pass_override = st.text_input(
                "Gmail App Password", type="password", value="", key="gmail_pass_in",
                help="Use a Google App Password, not your normal login password.",
            )
            gmail_user = st.session_state.get("gmail_user_override", "")
            gmail_pass = st.session_state.get("gmail_pass_override", "")

    gmail_user = GMAIL_USER or st.session_state.get("gmail_user_override", "")
    gmail_pass = GMAIL_PASS or st.session_state.get("gmail_pass_override", "")

    def build_email_html(patient_name, medicines, schedule, doctor_name, doctor_email, timing_label):
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
                f'No medicines for {timing_label or "this timing"}</td></tr>'
            )
        return f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#06070d;font-family:'Segoe UI',sans-serif">
        <div style="max-width:600px;margin:0 auto;padding:32px 16px">
            <div style="background:linear-gradient(135deg,#7c3aed,#3b82f6);border-radius:16px;padding:28px 32px;margin-bottom:24px;text-align:center">
            <div style="font-size:2.5rem;margin-bottom:8px">💊</div>
            <div style="font-size:1.4rem;font-weight:700;color:#fff">MedRemind</div>
            <div style="font-size:0.85rem;color:rgba(255,255,255,0.7);margin-top:4px">Medicine Reminder</div>
            </div>
            <div style="background:#0d1117;border:1px solid #1e293b;border-radius:14px;padding:24px 28px;margin-bottom:20px">
            <div style="font-size:1.1rem;font-weight:600;color:#f1f5f9;margin-bottom:8px">{icon} {timing_label} Reminder, {patient_name}!</div>
            <div style="font-size:0.88rem;color:#64748b;line-height:1.7">It's time to take your medicines. Please follow the dosage instructions carefully.</div>
            </div>
            <div style="background:#0d1117;border:1px solid #1e293b;border-radius:14px;padding:20px;margin-bottom:20px;overflow:hidden">
            <div style="font-size:0.78rem;font-weight:700;color:#a78bfa;text-transform:uppercase;letter-spacing:0.6px;margin-bottom:14px">📋 Your Medicines</div>
            <table style="width:100%;border-collapse:collapse">
                <thead><tr style="background:#1e293b">
                <th style="padding:10px 14px;text-align:left;color:#64748b;font-size:0.75rem;font-weight:600">Medicine</th>
                <th style="padding:10px 14px;text-align:left;color:#64748b;font-size:0.75rem;font-weight:600">Dose</th>
                <th style="padding:10px 14px;text-align:left;color:#64748b;font-size:0.75rem;font-weight:600">Duration</th>
                <th style="padding:10px 14px;text-align:left;color:#64748b;font-size:0.75rem;font-weight:600">Instructions</th>
                </tr></thead>
                <tbody>{schedule_rows}</tbody>
            </table>
            </div>
            <div style="text-align:center;padding:16px;font-size:0.78rem;color:#334155">
            Sent by <strong style="color:#a78bfa">MedRemind</strong> • Dr. {doctor_name}
            {'• ' + doctor_email if doctor_email else ''} • {datetime.now().strftime('%d %b %Y, %I:%M %p')}
            </div>
        </div></body></html>"""

    def send_email(to_email, patient_name, subject, html_body):
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = gmail_user
            msg["To"] = to_email
            msg.attach(MIMEText(html_body, "html"))
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(gmail_user, gmail_pass)
                server.sendmail(gmail_user, to_email, msg.as_string())
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    st.markdown('<div style="margin-top:1rem"></div>', unsafe_allow_html=True)
    patients = get_all_patients(user_id=get_current_user_id())
    patients_with_email = [p for p in patients if p.get("email") and "@" in p.get("email", "")]

    if not patients_with_email:
        st.markdown(
            '<div style="padding:2rem;text-align:center;border:1px dashed rgba(255,255,255,0.07);'
            'border-radius:16px;color:#475569">⚠️ No patients with email found. '
            'Add patient email in Patient Records first.</div>',
            unsafe_allow_html=True,
        )
    else:
        col1, col2 = st.columns([1.5, 1])
        with col1:
            patient_names = [f"{p['full_name']} ({p['email']})" for p in patients_with_email]
            selected = st.selectbox("Select Patient", patient_names, key="email_patient")
            sel_patient = patients_with_email[patient_names.index(selected)]
            timing = st.selectbox(
                "Reminder Timing", ["Morning", "Afternoon", "Evening", "Night"], key="email_timing"
            )
            doc_name = st.text_input("Doctor Name", value=doctor_name, key="email_doc")
            patient_schedule = build_schedule_from_db(sel_patient["email"])
            timing_meds = meds_for_timing(patient_schedule, timing)
            if timing_meds:
                med_choices = [
                    f"{i+1}. {m.get('name','—')} — {m.get('dose','').strip() or 'No dose'}"
                    for i, m in enumerate(timing_meds)
                ]
            else:
                med_choices = [
                    f"{i+1}. {m.get('name','—')} — {m.get('dose','').strip() or 'No dose'}"
                    for i, m in enumerate(patient_schedule)
                ]
            selected_meds_labels = st.multiselect(
                "Select medicine(s) to remind",
                med_choices,
                default=med_choices,
                key="email_med_select",
            )
            selected_meds = []
            for idx, label in enumerate(med_choices):
                if label in selected_meds_labels:
                    selected_meds.append(timing_meds[idx] if timing_meds else patient_schedule[idx])
            if not selected_meds:
                selected_meds = timing_meds or patient_schedule
            medicines_text = ", ".join([m.get("name", "—") for m in selected_meds]) or "—"
            use_schedule = selected_meds

        with col2:
            st.markdown(f"""
            <div style="background:#0d1117;border:1px solid rgba(167,139,250,0.2);border-radius:14px;padding:20px">
            <div style="font-size:0.75rem;font-weight:700;color:#a78bfa;text-transform:uppercase;margin-bottom:12px">Preview</div>
            <div style="font-size:0.85rem;color:#e2e8f0;margin-bottom:6px"><strong>To:</strong> {sel_patient['email']}</div>
            <div style="font-size:0.85rem;color:#e2e8f0;margin-bottom:6px"><strong>Patient:</strong> {sel_patient['full_name']}</div>
            <div style="font-size:0.85rem;color:#e2e8f0;margin-bottom:6px"><strong>Timing:</strong> {timing}</div>
            <div style="font-size:0.85rem;color:#e2e8f0"><strong>Medicines:</strong> {medicines_text[:60] + '...' if len(medicines_text) > 60 else medicines_text or '—'}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("📧 Send Reminder Email", use_container_width=True, key="send_now_btn"):
            if not gmail_user or not gmail_pass:
                st.error("❌ Gmail credentials missing! Add to .env or use the setup section above.")
            elif not sel_patient.get("email"):
                st.error("❌ Patient email not found!")
            elif not use_schedule:
                st.error("❌ No medicine selected for reminder!")
            else:
                html = build_email_html(
                    sel_patient["full_name"],
                    medicines_text,
                    use_schedule,
                    doc_name or "Your Doctor",
                    doctor_email,
                    timing,
                )
                with st.spinner(f"Sending email to {sel_patient['email']}..."):
                    result = send_email(
                        sel_patient["email"],
                        sel_patient["full_name"],
                        f"💊 MedRemind — {timing} Medicine Reminder",
                        html,
                    )
                if result["success"]:
                    log_email(sel_patient["email"], sel_patient["full_name"], timing, "sent", doctor_email=doctor_email)
                    st.success(f"✅ Email sent to {sel_patient['full_name']}!")
                else:
                    log_email(
                        sel_patient["email"], sel_patient["full_name"], timing,
                        f"failed: {result['error']}", doctor_email=doctor_email,
                    )
                    st.error(f"❌ Failed: {result['error']}")
