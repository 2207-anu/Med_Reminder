"""Top profile + navigation."""
import streamlit as st

from pages.admin_sections.shared import clear_user_workspace, render_profile_header

NAV_PAGES = [
    "Dashboard",
    "Prescription Upload",
    "Patient Records",
    "Email Reminder",
    "Activity",
]


def render_nav(user):
    render_profile_header(user)

    nav_cols = st.columns([0.01] + [1] * len(NAV_PAGES) + [0.65, 0.01])
    for i, page in enumerate(NAV_PAGES):
        with nav_cols[i + 1]:
            if st.button(
                page,
                key=f"anav_{page}",
                type="primary" if st.session_state.admin_nav == page else "secondary",
                use_container_width=True,
            ):
                st.session_state.admin_nav = page
                st.rerun()

    with nav_cols[-2]:
        if st.button("Logout", key="admin_logout", type="secondary", use_container_width=True):
            clear_user_workspace()
            st.session_state.admin_logged_in = False
            st.session_state.admin_user = None
            st.session_state.admin_user_email = None
            st.session_state.admin_auth_tab = "login"
            st.switch_page("App.py")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
