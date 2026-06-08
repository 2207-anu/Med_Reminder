"""MedRemind Admin — main entry (routes to section files)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from db_postgres import init_db
from pages.admin_sections.styles import inject
from pages.admin_sections import shared
from pages.admin_sections.nav import render_nav
from pages.admin_sections import dashboard
from pages.admin_sections import prescription_upload
from pages.admin_sections import patient_records
from pages.admin_sections import email_reminder
from pages.admin_sections import activity

st.set_page_config(page_title="MedRemind Admin", page_icon="👨‍⚕️", layout="wide")
init_db()
inject()
shared.init_session()
shared.check_gemini_keys()

if not st.session_state.admin_logged_in:
    st.switch_page("App.py")

user = st.session_state.admin_user
render_nav(user)

nav = st.session_state.admin_nav
if nav == "Dashboard":
    dashboard.render(user)
elif nav == "Prescription Upload":
    prescription_upload.render(user)
elif nav == "Patient Records":
    patient_records.render(user)
elif nav == "Email Reminder":
    email_reminder.render(user)
elif nav == "Activity":
    activity.render(user)
