"""Admin section: Dashboard."""
import streamlit as st

def render(user):
    st.markdown(f"""
    <div style="padding:1.25rem 0 0.75rem">
        <div style="font-family:'Syne',sans-serif;font-size:1.6rem;font-weight:800;color:#f1f5f9">
            Welcome, {user.get('full_name', 'Doctor')} 👋
        </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3, gap="medium")
    cards = [
        (c1, "📤", "Prescription Upload", "rgba(124,58,237,0.15)", "rgba(124,58,237,0.4)", "#c4b5fd",
        "Upload Prescription Images. AI reads, analyzes medicines &amp; builds dosage schedule."),
        (c2, "🗂️", "Patient Records", "rgba(6,182,212,0.12)", "rgba(6,182,212,0.3)", "#67e8f9",
        "Store and manage complete patient history, diagnoses &amp; doctor notes."),
        (c3, "📧", "Email Reminder", "rgba(34,197,94,0.12)", "rgba(34,197,94,0.3)", "#86efac",
        "Send automated medication reminders to patients via email."),
    ]
    for col, icon, title, bg, border, color, desc in cards:
        with col:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,{bg},{bg.replace('0.15','0.05').replace('0.12','0.04')});
                border:1px solid {border};border-radius:18px;padding:28px 24px">
            <div style="font-size:2.6rem;margin-bottom:14px">{icon}</div>
            <div style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;color:{color};margin-bottom:8px">{title}</div>
            <div style="font-size:0.85rem;color:#94a3b8;line-height:1.7">{desc}</div>
            </div>""", unsafe_allow_html=True)
