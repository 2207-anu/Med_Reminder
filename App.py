import re
import sys
from pathlib import Path
import time
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from db_postgres import init_db, login_user, register_user

st.set_page_config(page_title="MedRemind", page_icon="💊", layout="centered")
init_db()


def valid_email(e):
    return re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", e)


for k, v in {
    "admin_logged_in": False,
    "admin_user": None,
    "admin_auth_tab": "login",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


def clear_user_workspace():
    for key in list(st.session_state.keys()):
        if key.startswith("pr_") or key in (
            "extracted", "analysis", "context", "schedule", "reminders", "chat",
        ):
            del st.session_state[key]


if st.session_state.admin_logged_in:
    st.switch_page("pages/admin.py")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');
html, body, .stApp, section.main, .block-container {
    font-family: 'DM Sans', sans-serif !important;
    background-color: #06070d !important;
    color: #e2e8f0 !important;
}
#MainMenu, footer, header { visibility: hidden !important; }
[data-testid="stSidebar"] { display: none !important; }
.block-container { max-width: 440px !important; padding: 2rem 1rem !important; }
input, [data-testid="stTextInput"] input {
    background-color: #1a1f2e !important; color: #f1f5f9 !important;
    border: 1.5px solid #3b4a6a !important; border-radius: 10px !important;
}
input:focus { border-color: #7c3aed !important; box-shadow: 0 0 0 3px rgba(124,58,237,0.15) !important; }
.stButton > button {
    background: linear-gradient(135deg,#7c3aed,#3b82f6) !important;
    color: #fff !important; border: none !important; border-radius: 10px !important;
    font-weight: 600 !important;
}
.stButton > button[kind="secondary"] {
    background: rgba(255,255,255,0.04) !important;
    color: #94a3b8 !important; border: 1px solid rgba(255,255,255,0.08) !important;
}
.success-box { background:#052e16; border:1px solid #166534; border-radius:10px; padding:0.7rem 1rem; color:#86efac; font-size:0.9rem; }
.error-box { background:#2d0b0b; border:1px solid #7f1d1d; border-radius:10px; padding:0.7rem 1rem; color:#fca5a5; font-size:0.9rem; }
</style>
""", unsafe_allow_html=True)

_, mid, _ = st.columns([0.2, 1.6, 0.2])
with mid:
    st.markdown("""
    <div style="text-align:center;margin-bottom:1.5rem">
        <div style="font-size:2.5rem">💊</div>
        <div style="font-family:'Syne',sans-serif;font-size:1.5rem;font-weight:800;color:#c4b5fd">MedRemind</div>
        <div style="font-size:0.82rem;color:#475569;margin-top:4px">Doctor / staff login</div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        if st.button(
            "Login",
            use_container_width=True,
            type="primary" if st.session_state.admin_auth_tab == "login" else "secondary",
        ):
            st.session_state.admin_auth_tab = "login"
            st.rerun()
    with c2:
        if st.button(
            "Sign Up",
            use_container_width=True,
            type="primary" if st.session_state.admin_auth_tab == "signup" else "secondary",
        ):
            st.session_state.admin_auth_tab = "signup"
            st.rerun()

    st.markdown("---")

    if st.session_state.admin_auth_tab == "login":
        st.markdown("#### Login")
        email = st.text_input("Email", placeholder="your@email.com", key="auth_email")
        password = st.text_input("Password", type="password", placeholder="Enter password", key="auth_pass")
        if st.button("Login →", key="auth_submit", use_container_width=True, type="primary"):
            if not email or not password:
                st.markdown('<div class="error-box">Email and password required!</div>', unsafe_allow_html=True)
            elif not valid_email(email):
                st.markdown('<div class="error-box">Enter a valid email!</div>', unsafe_allow_html=True)
            else:
                result = login_user(email, password)
                if result["success"]:
                    if result["user"]["role"] != "admin":
                        st.markdown(
                            '<div class="error-box">Admin access only. Sign up as a doctor.</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        clear_user_workspace()
                        st.session_state.admin_logged_in = True
                        st.session_state.admin_user = result["user"]
                        st.session_state.admin_user_email = result["user"]["email"]
                        st.switch_page("pages/admin.py")
                else:
                    st.markdown(f'<div class="error-box">{result["message"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown("#### Sign Up")
        name = st.text_input("Full Name", placeholder="Dr. Sharma", key="auth_name")
        email = st.text_input("Email", placeholder="doctor@hospital.com", key="auth_su_email")
        password = st.text_input("Password", type="password", placeholder="Min 8 characters", key="auth_su_pass")
        confirm = st.text_input("Confirm Password", type="password", placeholder="Repeat password", key="auth_su_confirm")
        if st.button("Create Account →", key="auth_signup_submit", use_container_width=True, type="primary"):
            errors = []
            if not name.strip():
                errors.append("Name required")
            if not email:
                errors.append("Email required")
            elif not valid_email(email):
                errors.append("Invalid email")
            if not password:
                errors.append("Password required")
            elif len(password) < 8:
                errors.append("Min 8 characters")
            if password != confirm:
                errors.append("Passwords don't match")
            if errors:
                for e in errors:
                    st.markdown(f'<div class="error-box">{e}</div>', unsafe_allow_html=True)
            else:
                result = register_user(name, email, password, role="admin")
                if result["success"]:
                    st.markdown('<div class="success-box">Account created! Please login.</div>', unsafe_allow_html=True)
                    time.sleep(1)
                    st.session_state.admin_auth_tab = "login"
                    st.rerun()
                else:
                    st.markdown(f'<div class="error-box">{result["message"]}</div>', unsafe_allow_html=True)
