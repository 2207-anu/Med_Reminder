"""Admin global CSS."""
import streamlit as st

ADMIN_CSS = '''
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');
html, body, .stApp, section.main, .block-container {
    font-family: 'DM Sans', sans-serif !important;
    background-color: #06070d !important;
    color: #e2e8f0 !important;
    padding-top: 0 !important;
}
#MainMenu, footer, header { visibility: hidden !important; }
[data-testid="stSidebar"] { display: none !important; }
.block-container { padding-top:0 !important; padding-left:2.5rem !important; padding-right:2.5rem !important; max-width:1200px !important; }
input[type="text"], input[type="password"], [data-testid="stTextInput"] input, .stTextInput > div > div > input {
    background-color: #1a1f2e !important; color: #f1f5f9 !important;
    border: 1.5px solid #3b4a6a !important; border-radius: 10px !important;
    font-size: 0.95rem !important; caret-color: #a78bfa !important;
}
input::placeholder { color: #4a5568 !important; opacity: 1 !important; }
input:focus { border-color: #7c3aed !important; box-shadow: 0 0 0 3px rgba(124,58,237,0.15) !important; }
.stButton > button {
    background: linear-gradient(135deg,#7c3aed,#3b82f6) !important;
    color: #fff !important; border: none !important; border-radius: 10px !important;
    font-weight: 600 !important; padding: 0.6rem !important;
    font-family: 'DM Sans', sans-serif !important;
    box-shadow: 0 4px 20px rgba(124,58,237,0.25) !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover { opacity:0.85 !important; transform:translateY(-1px) !important; }
.stButton > button[kind="secondary"] {
    background: rgba(255,255,255,0.04) !important;
    color: #94a3b8 !important; border: 1px solid rgba(255,255,255,0.08) !important;
}
[data-testid="stFileUploader"] { background: #0d1117 !important; border-radius: 16px !important; }
[data-testid="stFileUploader"] > div, [data-testid="stFileUploader"] section {
    background: #0d1117 !important; border: 1.5px dashed rgba(167,139,250,0.5) !important; border-radius: 16px !important;
}
[data-testid="stFileUploader"] span, [data-testid="stFileUploader"] p,
[data-testid="stFileUploaderDropzoneInstructions"] span,
[data-testid="stFileUploaderDropzoneInstructions"] div { color: #a78bfa !important; }
[data-testid="stFileUploader"] button {
    background: rgba(124,58,237,0.2) !important; color: #c4b5fd !important;
    border: 1px solid rgba(167,139,250,0.3) !important; border-radius: 8px !important;
}
[data-testid="stFileUploader"] svg { fill: #a78bfa !important; stroke: #a78bfa !important; }
.success-box { background:#052e16; border:1px solid #166534; border-radius:10px; padding:0.7rem 1rem; color:#86efac; font-size:0.9rem; margin-top:0.5rem; }
.error-box   { background:#2d0b0b; border:1px solid #7f1d1d; border-radius:10px; padding:0.7rem 1rem; color:#fca5a5; font-size:0.9rem; margin-top:0.5rem; }
.sec-title { font-family:'Syne',sans-serif; font-size:1.5rem; font-weight:800; color:#f1f5f9; letter-spacing:-0.5px; margin:28px 0 4px; }
.sec-sub { color:#475569; font-size:0.85rem; margin-bottom:22px; }
.glass-card { background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.07); border-radius:18px; padding:24px 26px; margin-bottom:18px; }
.glass-card-title { font-family:'Syne',sans-serif; font-size:0.85rem; font-weight:700; color:#a78bfa; text-transform:uppercase; letter-spacing:0.6px; margin-bottom:14px; }
.divider { border:none; border-top:1px solid rgba(255,255,255,0.06); margin:8px 0 20px; }
.navbar { display:flex; align-items:center; background:#0d1117; border-bottom:1px solid #1e3a5f; padding:0 1.5rem; height:56px; position:sticky; top:0; z-index:999; }
.navbar-logo { font-family:'Syne',sans-serif; font-size:1.15rem; font-weight:700; color:#a78bfa; white-space:nowrap; margin-right:1rem; }
.navbar-role { background:rgba(124,58,237,0.15); border:1px solid rgba(124,58,237,0.3); color:#c4b5fd; border-radius:6px; padding:3px 10px; font-size:0.75rem; font-weight:600; }
.med-pill-card { background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.07); border-radius:16px; padding:20px 22px; margin-bottom:14px; transition:border-color 0.2s; }
.med-pill-card:hover { border-color:rgba(167,139,250,0.3); }
.med-pill-card h4 { font-family:'Syne',sans-serif; font-size:0.98rem; font-weight:700; color:#c4b5fd; margin-bottom:10px; }
.meta-grid { display:flex; gap:24px; flex-wrap:wrap; margin-bottom:10px; }
.meta-cell { font-size:0.8rem; }
.meta-cell span { display:block; color:#475569; margin-bottom:2px; font-size:0.72rem; text-transform:uppercase; letter-spacing:0.5px; }
.meta-cell strong { color:#94a3b8; }
.tbadge { display:inline-flex; align-items:center; gap:5px; background:rgba(167,139,250,0.08); border:1px solid rgba(167,139,250,0.18); color:#c4b5fd; border-radius:8px; padding:4px 11px; font-size:0.77rem; margin:3px 4px 3px 0; }
.mrow { display:flex; align-items:flex-end; gap:9px; animation:msgPop 0.2s ease; }
.mrow.u { flex-direction:row-reverse; }
@keyframes msgPop { from{opacity:0;transform:translateY(6px)} to{opacity:1;transform:translateY(0)} }
.mava { width:27px; height:27px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:12px; flex-shrink:0; }
.ba { background:linear-gradient(135deg,#7c3aed,#3b82f6); }
.ua { background:linear-gradient(135deg,#0ea5e9,#06b6d4); }
.bub { max-width:65%; padding:10px 15px; border-radius:18px; font-size:0.87rem; line-height:1.6; word-wrap:break-word; }
.bb { background:rgba(255,255,255,0.06); color:#e2e8f0; border-bottom-left-radius:4px; }
.ub { background:linear-gradient(135deg,#3b82f6,#2563eb); color:#fff; border-bottom-right-radius:4px; }
.mtime { font-size:0.62rem; color:#475569; margin-top:3px; padding:0 4px; }
.mrow.u .mtime { text-align:right; }
.stSelectbox > div > div {
    background-color: #1a1f2e !important;
    color: #f1f5f9 !important;
    border: 1.5px solid #3b4a6a !important;
    border-radius: 10px !important;
}
.stSelectbox > div > div > div { color: #f1f5f9 !important; }
.stSelectbox svg { fill: #a78bfa !important; }
[data-baseweb="select"] { background-color: #1a1f2e !important; }
[data-baseweb="popover"] ul { background-color: #1a1f2e !important; border: 1px solid #3b4a6a !important; }
[data-baseweb="popover"] li { color: #f1f5f9 !important; }
[data-baseweb="popover"] li:hover { background-color: rgba(167,139,250,0.15) !important; }
[data-baseweb="option"][aria-selected="true"] { background-color: rgba(124,58,237,0.25) !important; }

.app-topbar {
    display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;
    background: rgba(13,17,23,0.95); backdrop-filter: blur(12px);
    border-bottom: 1px solid rgba(255,255,255,0.06);
    padding: 0.65rem 1.5rem; margin: 0 -2.5rem 0; position: sticky; top: 0; z-index: 999;
}
.app-topbar-left { display: flex; align-items: center; gap: 14px; }
.app-brand {
    font-family: 'Syne', sans-serif; font-size: 1.1rem; font-weight: 800;
    color: #f1f5f9; letter-spacing: -0.3px;
}
.app-brand span { color: #a78bfa; }

.profile-menu {
    display: flex; align-items: center; gap: 12px;
    background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px; padding: 6px 10px 6px 6px;
}
.profile-avatar {
    width: 38px; height: 38px; border-radius: 50%; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    font-family: 'Syne', sans-serif; font-size: 0.95rem; font-weight: 800; color: #fff;
    background: linear-gradient(135deg, #7c3aed, #3b82f6);
    box-shadow: 0 4px 14px rgba(124,58,237,0.35);
}
.profile-info { line-height: 1.25; min-width: 0; }
.profile-name {
    font-size: 0.82rem; font-weight: 600; color: #f1f5f9;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 180px;
}
.profile-email {
    font-size: 0.72rem; color: #64748b;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 200px;
}
.profile-role {
    font-size: 0.65rem; font-weight: 600; color: #a78bfa;
    text-transform: uppercase; letter-spacing: 0.4px;
}
</style>
'''

def inject():
    st.markdown(ADMIN_CSS, unsafe_allow_html=True)
