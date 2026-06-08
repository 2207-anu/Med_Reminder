"""Admin section: Activity."""
import streamlit as st

from pages.admin_sections.shared import get_current_user_id

def render(user):
    from db_postgres import get_all_patients, get_all_schedules, get_email_logs

    dash_user_id = get_current_user_id()
    dash_doctor_email = user.get("email", "")
    st.markdown('<div class="sec-title">📊 Activity</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="sec-sub">Your patients, schedules &amp; email history '
        f'(<strong style="color:#a78bfa">{dash_doctor_email}</strong>).</div>',
        unsafe_allow_html=True,
    )

    tab1, tab2, tab3 = st.tabs(["👥 All Patients", "📅 Schedules", "📬 Email Logs"])

    with tab1:
        patients = get_all_patients(user_id=dash_user_id)
        if not patients:
            st.markdown('<div style="padding:2rem;text-align:center;color:#475569;border:1px dashed rgba(255,255,255,0.07);border-radius:14px">No patients yet.</div>', unsafe_allow_html=True)
        else:
            for p in patients:
                st.markdown(f"""
                <div style="background:#0d1117;border:1px solid #1e293b;border-radius:14px;
                    padding:16px 20px;margin-bottom:10px;display:flex;gap:20px;flex-wrap:wrap">
                <div style="font-size:0.82rem"><span style="color:#475569;font-size:0.72rem;display:block;text-transform:uppercase">Name</span><strong style="color:#e2e8f0">{p['full_name']}</strong></div>
                <div style="font-size:0.82rem"><span style="color:#475569;font-size:0.72rem;display:block;text-transform:uppercase">Email</span><strong style="color:#67e8f9">{p['email'] or '—'}</strong></div>
                <div style="font-size:0.82rem"><span style="color:#475569;font-size:0.72rem;display:block;text-transform:uppercase">Disease</span><strong style="color:#c4b5fd">{p['disease'] or '—'}</strong></div>
                <div style="font-size:0.82rem"><span style="color:#475569;font-size:0.72rem;display:block;text-transform:uppercase">Added By Email</span><strong style="color:#fbbf24">{p.get('creator_email') or p.get('added_by_email') or p.get('owner_email') or '—'}</strong></div>
                <div style="font-size:0.82rem"><span style="color:#475569;font-size:0.72rem;display:block;text-transform:uppercase">Patient Email</span><strong style="color:#67e8f9">{p.get('email') or '—'}</strong></div>
                </div>""", unsafe_allow_html=True)

    with tab2:
        schedules = get_all_schedules(user_id=dash_user_id)
        if not schedules:
            st.markdown('<div style="padding:2rem;text-align:center;color:#475569;border:1px dashed rgba(255,255,255,0.07);border-radius:14px">No schedules yet.</div>', unsafe_allow_html=True)
        else:
            time_icons = {"Morning":"🌅","Afternoon":"☀️","Evening":"🌆","Night":"🌙"}
            for s in schedules:
                with st.expander(f"📋 {s['patient_name']} ({s['patient_email']})"):
                    for med in s["schedule"]:
                        times = med.get("times",[])
                        if isinstance(times, str): times = [t.strip() for t in times.split(",")]
                        badges = " ".join([f'<span style="background:rgba(167,139,250,0.1);border:1px solid rgba(167,139,250,0.2);color:#c4b5fd;border-radius:6px;padding:2px 8px;font-size:0.75rem">{time_icons.get(t,"💊")} {t}</span>' for t in times])
                        st.markdown(f"""
                        <div style="background:#0d1117;border:1px solid #1e293b;border-radius:10px;padding:12px 16px;margin-bottom:8px">
                        <strong style="color:#a78bfa">{med.get('name','—')}</strong>
                        <span style="color:#64748b;font-size:0.8rem;margin-left:10px">{med.get('dose','')}</span>
                        <div style="margin-top:6px">{badges}</div>
                        </div>""", unsafe_allow_html=True)

    with tab3:
        logs = get_email_logs(50, doctor_email=dash_doctor_email)
        if not logs:
            st.markdown('<div style="padding:2rem;text-align:center;color:#475569;border:1px dashed rgba(255,255,255,0.07);border-radius:14px">No emails sent yet.</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="font-size:0.82rem;color:#475569;margin-bottom:16px">Last <strong style="color:#a78bfa">{len(logs)}</strong> emails</div>', unsafe_allow_html=True)
            for log in logs:
                ok = log["status"] in ("success", "sent")
                color  = "#86efac" if ok else "#fca5a5"
                icon   = "✅" if ok else "❌"
                timing_icon = {"Morning":"🌅","Afternoon":"☀️","Evening":"🌆","Night":"🌙"}.get(log["timing"],"💊")
                st.markdown(f"""
                <div style="background:#0d1117;border:1px solid #1e293b;border-radius:10px;
                    padding:10px 16px;margin-bottom:6px;display:flex;gap:16px;align-items:center;flex-wrap:wrap">
                <span style="color:{color};font-size:0.85rem">{icon}</span>
                <span style="color:#e2e8f0;font-size:0.83rem"><strong>{log['patient_name']}</strong></span>
                <span style="color:#64748b;font-size:0.8rem">{log['patient_email']}</span>
                <span style="color:#a78bfa;font-size:0.8rem">{timing_icon} {log['timing']}</span>
                <span style="color:#334155;font-size:0.75rem;margin-left:auto">{log['sent_at']}</span>
                </div>""", unsafe_allow_html=True)