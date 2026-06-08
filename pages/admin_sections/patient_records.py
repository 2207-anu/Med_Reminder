"""Admin section: Patient Records."""
import streamlit as st

import re, json
from PIL import Image
import pandas as pd
from pages.admin_sections.shared import *

def render(user):
    from db_postgres import add_patient, get_all_patients, delete_patient

    owner_id = get_current_user_id()
    st.markdown('<div class="sec-title">🗂️ Patient Records</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="sec-sub">Your patients only — linked to '
        f'<strong style="color:#a78bfa">{user.get("email", "")}</strong>.</div>',
        unsafe_allow_html=True,
    )

    tab1, tab2 = st.tabs(["📋 All Patients", "➕ Add New Patient"])

    # ══ TAB 1: ALL PATIENTS ══
    with tab1:
        patients = get_all_patients(user_id=owner_id)
        if not patients:
            st.markdown("""
            <div style="padding:2.5rem;text-align:center;border:1px dashed rgba(255,255,255,0.07);
            border-radius:16px;color:#475569;margin-top:1rem">
            <div style="font-size:3rem;margin-bottom:12px">🗂️</div>
            <div style="font-size:0.95rem">No patients added yet.</div>
            <div style="font-size:0.82rem;margin-top:6px">Use the <strong style="color:#a78bfa">Add New Patient</strong> tab to add one.</div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="font-size:0.82rem;color:#475569;margin-bottom:16px">Total: <strong style="color:#a78bfa">{len(patients)}</strong> patients</div>', unsafe_allow_html=True)
            search = st.text_input("🔍 Search by name or disease", placeholder="e.g. Rahul or Diabetes", key="pr_search")
            filtered = [p for p in patients if
                        search.lower() in p["full_name"].lower() or
                        search.lower() in (p["disease"] or "").lower()
                    ] if search else patients

            for p in filtered:
                creator = p.get("creator_email") or p.get("added_by_email") or p.get("owner_email") or "—"
                with st.expander(
                    f"👤 {p['full_name']}  •  {p['disease'] or 'No disease info'}  •  Added by: {creator}"
                ):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.markdown(f"""
                        <div class="glass-card">
                        <div class="glass-card-title">Personal Info</div>
                        <div class="meta-grid">
                            <div class="meta-cell"><span>Full Name</span><strong>{p['full_name']}</strong></div>
                            <div class="meta-cell"><span>Age</span><strong>{p['age'] or '—'}</strong></div>
                            <div class="meta-cell"><span>Gender</span><strong>{p['gender'] or '—'}</strong></div>
                        </div>
                        </div>""", unsafe_allow_html=True)
                    with c2:
                        st.markdown(f"""
                        <div class="glass-card">
                        <div class="glass-card-title">Contact</div>
                        <div class="meta-grid">
                            <div class="meta-cell"><span>Phone</span><strong>{p['phone'] or '—'}</strong></div>
                            <div class="meta-cell"><span>Patient Email</span><strong>{p['email'] or '—'}</strong></div>
                            <div class="meta-cell"><span>Added By (Doctor)</span><strong>{creator}</strong></div>
                            <div class="meta-cell"><span>Date</span><strong>{p['prescription_date'] or '—'}</strong></div>
                        </div>
                        </div>""", unsafe_allow_html=True)
                    with c3:
                        st.markdown(f"""
                        <div class="glass-card">
                        <div class="glass-card-title">Medical Info</div>
                        <div class="meta-grid">
                            <div class="meta-cell"><span>Disease</span><strong>{p['disease'] or '—'}</strong></div>
                        </div>
                        </div>""", unsafe_allow_html=True)

                    if p['doctor_notes']:
                        st.markdown(f"""
                        <div style="background:rgba(167,139,250,0.07);border:1px solid rgba(167,139,250,0.2);
                        border-radius:12px;padding:14px 18px;font-size:0.85rem;color:#c4b5fd;line-height:1.7;margin-top:4px">
                        📝 <strong>Doctor Notes:</strong> {p['doctor_notes']}
                        </div>""", unsafe_allow_html=True)

                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button(f"🗑️ Delete Patient", key=f"del_{p['id']}"):
                        del_result = delete_patient(p['id'], user_id=owner_id)
                        if del_result.get("success"):
                            st.success("Patient deleted successfully!")
                            st.rerun()
                        else:
                            st.error("Could not delete — patient not found or access denied.")

    # ══ TAB 2: ADD NEW PATIENT ══
    with tab2:
        st.markdown('<div style="margin-top:1rem"></div>', unsafe_allow_html=True)

        if st.session_state.get("pr_save_msg"):
            st.markdown(
                f'<div class="success-box">{st.session_state.pr_save_msg}</div>',
                unsafe_allow_html=True,
            )

        def extract_patient_data(image, raw_text):
            prompt = f"""
            This is handwritten text from a prescription (printed text has already been removed):
            {raw_text}

            Extract patient details from ONLY this handwritten content.
            Ignore anything that looks like hospital name, clinic address, doctor stamp, or pre-printed letterhead.
            Only use what was handwritten by the doctor or patient.

            {ENGLISH_ONLY_RULE}
            Every JSON string value must be in English (translate names, disease, notes, medicines if needed).

            Return ONLY a valid JSON object. No explanation, no markdown.
            Fields:
            {{
              "full_name": "patient name or empty string",
              "age": "age as string or empty string",
              "gender": "Male or Female or Other or empty string",
              "phone": "phone number or empty string",
              "email": "email or empty string",
              "disease": "diagnosis or disease name or empty string",
              "medicines": "comma separated medicine names with doses or empty string",
              "prescription_date": "date in DD/MM/YYYY or empty string",
              "doctor_notes": "any special instructions or empty string"
            }}
            If any field not found in handwritten text, use empty string.
            """
            raw = gemini_call(prompt)
            raw = re.sub(r"```(?:json)?", "", raw.strip()).strip("` \n")
            try:
                return json.loads(raw)
            except:
                return {}

        left, right = st.columns([1, 1], gap="large")

        with left:
            st.markdown('<div style="font-size:0.85rem;color:#a78bfa;font-weight:600;margin-bottom:8px">📤 Upload Prescription</div>', unsafe_allow_html=True)
            pr_uploaded = st.file_uploader("", type=["jpg","png","jpeg"], key="pr_upload", label_visibility="collapsed")
            pr_img = None
            if pr_uploaded:
                pr_img = Image.open(pr_uploaded)
                st.image(pr_img, use_container_width=True, caption="Uploaded prescription")

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🤖 Extract Patient Data", use_container_width=True, key="pr_extract_btn"):
                if pr_img is None:
                    st.warning("⚠️ Please upload an image first!")
                else:
                    with st.spinner("📖 Reading prescription..."):
                        raw_text = extract_text(pr_img)
                    if is_error(raw_text):
                        st.error(f"❌ Could not read prescription: {raw_text}")
                        st.info("💡 Server busy — wait 10 seconds and try again.")
                        st.stop()
                    with st.spinner("🤖 Extracting patient data..."):
                        patient_data = extract_patient_data(pr_img, raw_text)
                    with st.spinner("📅 Building medicine schedule..."):
                        schedule = parse_schedule(raw_text)
                    with st.spinner("💊 Loading all medicines and uses..."):
                        confirmed = build_confirmed_meds_from_schedule(schedule)
                    st.session_state.pr_extracted_data = patient_data
                    st.session_state.pr_raw_text       = raw_text
                    st.session_state.pr_schedule       = schedule
                    st.session_state.pr_confirmed_meds = confirmed
                    st.session_state.pr_save_msg       = None
                    st.session_state.pr_saved_patient_id = None
                    st.success("✅ Data extracted! Verify on the right.")

        # ══════════════════════════════════════════
        #  RIGHT COLUMN — VERIFY PATIENT INFO
        # ══════════════════════════════════════════
        with right:
            if "pr_extracted_data" in st.session_state and st.session_state.pr_extracted_data:
                d = st.session_state.pr_extracted_data
                st.markdown('<div style="font-size:0.85rem;color:#a78bfa;font-weight:600;margin-bottom:12px">✏️ Verify Patient Info</div>', unsafe_allow_html=True)

                fname   = st.text_input("Full Name *", value=d.get("full_name",""), key="prf_name")
                c1, c2  = st.columns(2)
                with c1: age = st.text_input("Age", value=d.get("age",""), key="prf_age")
                with c2:
                    gender_opts = ["Select","Male","Female","Other"]
                    gender_val  = d.get("gender","Select")
                    gender_idx  = gender_opts.index(gender_val) if gender_val in gender_opts else 0
                    gender      = st.selectbox("Gender", gender_opts, index=gender_idx, key="prf_gender")
                c3, c4  = st.columns(2)
                with c3: phone = st.text_input("Phone", value=d.get("phone",""), key="prf_phone")
                with c4: email = st.text_input("Email", value=d.get("email",""), key="prf_email")
                date    = st.text_input("Prescription Date", value=d.get("prescription_date",""), key="prf_date")
                disease = st.text_input("Disease / Diagnosis", value=d.get("disease",""), key="prf_disease")
                notes   = st.text_area("Doctor Notes", value=d.get("doctor_notes",""), height=80, key="prf_notes")

                st.markdown("<br>", unsafe_allow_html=True)

                # ── Save Patient ONLY (no medicines) ──────────────────────
                # FIX: Removed medicines= kwarg — add_patient() has no such param
                if st.button("💾 Save Patient to DB", use_container_width=True, key="save_patient_only_btn"):
                    result = persist_patient_record()
                    if result.get("success"):
                        v = read_patient_form_values()
                        st.session_state.pr_save_msg = (
                            f"✅ <strong>{v['fname']}</strong> saved to All Patients "
                            f"(ID: {result['patient_id']}). You can add medicines below and save once."
                        )
                    else:
                        st.error(f"❌ {result.get('message', 'Save failed')}")

            else:
                st.markdown("""
                <div style="height:380px;display:flex;flex-direction:column;align-items:center;
                     justify-content:center;text-align:center;
                     border:1px dashed rgba(167,139,250,0.15);border-radius:18px;gap:12px">
                  <div style="font-size:4rem;opacity:0.15">🤖</div>
                  <div style="font-family:'Syne',sans-serif;font-size:0.9rem;font-weight:700;color:#334155">
                    Auto-filled data will appear here
                  </div>
                  <div style="font-size:0.8rem;color:#1e293b;max-width:220px;line-height:1.6">
                    Upload a prescription and click Extract
                  </div>
                </div>""", unsafe_allow_html=True)

        # ══ MEDICINES SECTION ══
        if "pr_schedule" in st.session_state and st.session_state.pr_schedule:
            st.markdown("<hr style='border-color:rgba(255,255,255,0.06);margin:24px 0'>", unsafe_allow_html=True)
            st.markdown("""
            <div style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;
                 color:#f1f5f9;margin-bottom:4px">💊 Add Medicines</div>
            <div style="font-size:0.8rem;color:#475569;margin-bottom:16px">
                 All medicines from the prescription appear below. Edit name, uses, or duration; delete any you do not need.<br>
                 Uses are filled automatically. Use <strong style="color:#a78bfa">Save Medicines to DB</strong> to save patient + medicines together.
            </div>""", unsafe_allow_html=True)

            if st.session_state.get("pr_saved_patient_id"):
                st.markdown(
                    f'<div style="font-size:0.8rem;color:#86efac;margin-bottom:12px">'
                    f'🔗 Linked patient ID: <strong>{st.session_state.pr_saved_patient_id}</strong> '
                    f'— re-save will update the same record.</div>',
                    unsafe_allow_html=True,
                )

            schedule   = st.session_state.pr_schedule
            time_icons = {"Morning":"🌅","Afternoon":"☀️","Evening":"🌆","Night":"🌙"}

            if "pr_confirmed_meds" not in st.session_state:
                st.session_state.pr_confirmed_meds = []

            if not st.session_state.pr_confirmed_meds and schedule:
                st.session_state.pr_confirmed_meds = build_confirmed_meds_from_schedule(schedule)

            if schedule:
                hdr1, hdr2 = st.columns([1, 1])
                with hdr1:
                    st.markdown(
                        f'<div style="font-size:0.85rem;color:#a78bfa;font-weight:600">'
                        f'📋 All Medicines ({len(st.session_state.pr_confirmed_meds)})</div>',
                        unsafe_allow_html=True,
                    )
                with hdr2:
                    if st.button("🔄 Reload from prescription", key="pr_reload_meds_btn"):
                        st.session_state.pr_confirmed_meds = build_confirmed_meds_from_schedule(schedule)
                        st.rerun()

            if not st.session_state.pr_confirmed_meds:
                st.markdown(
                    '<div style="font-size:0.82rem;color:#fca5a5;margin-bottom:12px">'
                    '⚠️ No medicines found on this prescription.</div>',
                    unsafe_allow_html=True,
                )

            # ── Added medicines editable table ──
            if st.session_state.pr_confirmed_meds:
                st.markdown('<div style="font-size:0.85rem;color:#a78bfa;font-weight:600;margin:16px 0 10px">📋 Added Medicines</div>', unsafe_allow_html=True)
                st.markdown('<div style="font-size:0.78rem;color:#64748b;margin-bottom:8px">✏️ You can edit any field directly in the table below.</div>', unsafe_allow_html=True)

                import pandas as pd

                def meds_to_df(meds):
                    rows = []
                    for m in meds:
                        times_list = normalize_med_times(m.get("times", []))
                        times_str = ", ".join(times_list) if times_list else ""
                        rows.append({
                            "Medicine":  m.get("name", ""),
                            "Dose":      m.get("dose", "") or "",
                            "Uses":      (m.get("uses") or m.get("instructions") or ""),
                            "Timing":    times_str,
                            "Duration":  m.get("duration", "") or "",
                        })
                    return pd.DataFrame(rows)

                edited_df = st.data_editor(
                    meds_to_df(st.session_state.pr_confirmed_meds),
                    use_container_width=True,
                    num_rows="dynamic",
                    key="meds_editor",
                    column_config={
                        "Medicine":  st.column_config.TextColumn("Medicine",  width="medium"),
                        "Dose":      st.column_config.TextColumn("Dose",      width="small"),
                        "Uses":      st.column_config.TextColumn("Uses (What it Treats)", width="large"),
                        "Timing":    st.column_config.TextColumn("Timing",    width="medium",
                                        help="e.g. Morning, Night"),
                        "Duration":  st.column_config.TextColumn("Duration",  width="small"),
                    },
                )

                # Sync edits back to session state
                updated_meds = []
                for _, row in edited_df.iterrows():
                    if str(row.get("Medicine", "")).strip():
                        timing_raw = str(row.get("Timing", "")).strip()
                        times_list = [t.strip() for t in timing_raw.split(",") if t.strip()]
                        updated_meds.append({
                            "name":         str(row.get("Medicine", "")).strip(),
                            "dose":         str(row.get("Dose", "")).strip(),
                            "uses":         str(row.get("Uses", "")).strip(),
                            "instructions": str(row.get("Uses", "")).strip(),
                            "times":        times_list,
                            "duration":     str(row.get("Duration", "")).strip(),
                        })
                st.session_state.pr_confirmed_meds = updated_meds

                st.markdown("<br>", unsafe_allow_html=True)

                # ── Save medicines (also saves/updates patient — one record) ──
                if st.button("💾 Save Medicines to DB", use_container_width=True, key="pr_save_btn"):
                    from db_postgres import save_prescription_schedule, save_confirmed_medicines

                    v = read_patient_form_values()
                    if not v["fname"].strip():
                        st.error("❌ Enter Patient Name in Verify Patient Info (right side) before saving.")
                    elif not st.session_state.pr_confirmed_meds:
                        st.error("❌ Add at least one medicine before saving.")
                    else:
                        result = persist_patient_record()
                        if not result.get("success"):
                            st.error(f"❌ {result.get('message', 'Patient save failed')}")
                        else:
                            patient_id = result["patient_id"]
                            email_clean = v["email"].lower().strip() if v["email"] else ""
                            storage_email = email_clean or f"patient_{patient_id}@medremind.local"

                            sched_result = save_prescription_schedule(
                                patient_id=patient_id,
                                patient_email=storage_email,
                                patient_name=v["fname"].strip(),
                                schedule_list=st.session_state.pr_confirmed_meds,
                                extracted_text=st.session_state.get("pr_raw_text", ""),
                            )
                            meds_result = save_confirmed_medicines(
                                patient_id=patient_id,
                                patient_email=storage_email,
                                patient_name=v["fname"].strip(),
                                medicines_list=st.session_state.pr_confirmed_meds,
                            )

                            if not sched_result.get("success", False):
                                st.error(f"❌ Schedule save failed: {sched_result.get('message', 'Unknown error')}")
                            elif not meds_result.get("success", False):
                                st.error(f"❌ Medicines save failed: {meds_result.get('message', 'Unknown error')}")
                            else:
                                med_count = len(st.session_state.pr_confirmed_meds)
                                st.session_state.pr_save_msg = (
                                    f"✅ <strong>{v['fname']}</strong> is in All Patients and "
                                    f"<strong>{med_count} medicines</strong> saved (Patient ID: {patient_id})."
                                )
