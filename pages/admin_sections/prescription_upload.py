"""Admin section: Prescription Upload."""
import streamlit as st

from datetime import datetime
from PIL import Image
from pages.admin_sections.shared import *

def render(user):
    nav_col1, nav_col2, nav_col3, nav_spacer = st.columns([1,1,1,5])
    with nav_col1:
        if st.button("📤 Upload", use_container_width=True, key="rx_nav_upload"):
            st.session_state.rx_page = "Upload"; st.rerun()
    with nav_col2:
        if st.button("💬 Chatbot", use_container_width=True, key="rx_nav_chat"):
            st.session_state.rx_page = "Chatbot"; st.rerun()
    with nav_col3:
        if st.button("📅 Schedule", use_container_width=True, key="rx_nav_sched"):
            st.session_state.rx_page = "Schedule"; st.rerun()
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── UPLOAD PAGE ──
    if st.session_state.rx_page == "Upload":
        left_col, right_col = st.columns([1,1], gap="large")
        with left_col:
            st.markdown('<div class="sec-title">Upload Prescription</div>', unsafe_allow_html=True)
            st.markdown('<div class="sec-sub">Supports JPG, PNG, JPEG • Max 200MB per file</div>', unsafe_allow_html=True)
            uploaded = st.file_uploader("", type=["jpg","png","jpeg"], label_visibility="collapsed")
            img = None
            if uploaded:
                img = Image.open(uploaded)
                st.image(img, use_container_width=True, caption="Uploaded prescription")
            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("⚡ Analyze Prescription", use_container_width=True):
                if img is None:
                    st.warning("⚠️ Please upload an image first.")
                else:
                    with st.spinner("📖 Reading prescription..."):
                        text = extract_text(img)
                    if is_error(text):
                        st.error(f"❌ Text extraction failed: {text}")
                        st.info("💡 Gemini server busy — please wait 10 seconds and try again.")
                        st.stop()
                    with st.spinner("🔍 Analyzing medicines..."):
                        analysis = analyze(text)
                    if is_error(analysis):
                        st.error(f"❌ Medicine analysis failed: {analysis}")
                        st.session_state.extracted = text
                        st.stop()
                    with st.spinner("📅 Building schedule..."):
                        schedule = parse_schedule(text)
                    st.session_state.extracted  = text
                    st.session_state.analysis   = analysis
                    st.session_state.context    = text + "\n" + analysis
                    st.session_state.schedule   = schedule if schedule else []
                    st.session_state.reminders  = {m["name"]: m.get("times", []) for m in (schedule or [])}
                    st.session_state.chat       = []
                    st.success("✅ Analysis complete!")

        with right_col:
            if "extracted" in st.session_state:
                extracted_text = st.session_state.extracted
                st.markdown(f'<div class="glass-card"><div class="glass-card-title">📝 Extracted Text</div><pre style="background:#0d1117;border:1px solid rgba(167,139,250,0.2);border-radius:12px;padding:16px 18px;font-size:0.83rem;color:#e2e8f0;line-height:1.8;white-space:pre-wrap;word-wrap:break-word;margin:0">{extracted_text}</pre></div>', unsafe_allow_html=True)
                if "analysis" in st.session_state:
                    st.markdown('<div class="glass-card"><div class="glass-card-title">🔍 Medicine Analysis</div></div>', unsafe_allow_html=True)
                    st.markdown(f'<div style="color:#cbd5e1;font-size:0.87rem;line-height:1.75;padding:4px 0">{st.session_state.analysis.replace(chr(10),"<br>")}</div>', unsafe_allow_html=True)
                    if st.session_state.schedule:
                        st.markdown('<div style="margin-top:20px;background:rgba(167,139,250,0.07);border:1px solid rgba(167,139,250,0.2);border-radius:12px;padding:14px 18px;font-size:0.84rem;color:#a78bfa;line-height:1.6">✅ Schedule detected! Click 📅 Schedule above.</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div style="height:420px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;border:1px dashed rgba(255,255,255,0.06);border-radius:18px;gap:12px"><div style="font-size:4.5rem;opacity:0.2">🩺</div><div style="font-family:\'Syne\',sans-serif;font-size:0.95rem;font-weight:700;color:#334155">Results appear here</div><div style="font-size:0.8rem;color:#1e293b;max-width:220px;line-height:1.6">Upload and click Analyze</div></div>', unsafe_allow_html=True)

    # ── CHATBOT PAGE ──
    elif st.session_state.rx_page == "Chatbot":
        st.markdown('<div class="sec-title">💬 Ask About Prescription</div>', unsafe_allow_html=True)
        if "context" not in st.session_state or not st.session_state.context:
            st.markdown('<div style="padding:2rem;text-align:center;border:1px dashed rgba(255,255,255,0.07);border-radius:16px;color:#475569">⚠️ Please upload and analyze a prescription from the <strong style="color:#a78bfa">Upload</strong> tab.</div>', unsafe_allow_html=True)
        else:
            msgs_html = ""
            for msg in st.session_state.chat:
                t = msg.get("time","")
                if msg["role"]=="user":
                    msgs_html += f'<div class="mrow u"><div class="mava ua">🧑</div><div><div class="bub ub">{msg["text"]}</div><div class="mtime">{t}</div></div></div>'
                else:
                    msgs_html += f'<div class="mrow"><div class="mava ba">🤖</div><div><div class="bub bb">{msg["text"]}</div><div class="mtime">{t}</div></div></div>'
            if not msgs_html:
                msgs_html = '<div style="flex:1;display:flex;align-items:center;justify-content:center;color:#334155;font-size:0.85rem">💬 Ask anything about your prescription</div>'
            st.markdown(f'<div style="display:flex;flex-direction:column;height:55vh;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.07);border-radius:20px;overflow:hidden"><div style="display:flex;align-items:center;gap:12px;padding:14px 20px;background:rgba(255,255,255,0.03);border-bottom:1px solid rgba(255,255,255,0.06)"><div style="width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg,#7c3aed,#3b82f6);display:flex;align-items:center;justify-content:center;font-size:16px">🤖</div><strong style="font-family:\'Syne\',sans-serif;color:#f1f5f9">MedRemind AI</strong><span style="font-size:0.75rem;color:#22c55e">● Online</span></div><div style="flex:1;overflow-y:auto;padding:18px 16px;display:flex;flex-direction:column;gap:14px">{msgs_html}</div></div>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            user_q = st.text_input("", placeholder="e.g. What are the side effects?", key="chat_input", label_visibility="collapsed")
            if st.button("Send ➤", key="chat_send"):
                if user_q.strip():
                    st.session_state.chat.append({"role":"user","text":user_q,"time":datetime.now().strftime("%I:%M %p")})
                    with st.spinner("Thinking..."):
                        reply = gemini_call(
                            f"Medical assistant. Answer based on context only.\n"
                            f"{ENGLISH_ONLY_RULE}\n"
                            f"Context: {st.session_state.context}\n"
                            f"Question: {user_q}\n"
                            f"Reply in simple English only, concise."
                        )
                    if is_error(reply):
                        reply = "⚠️ Server busy. Please try again in a moment."
                    st.session_state.chat.append({"role":"bot","text":reply,"time":datetime.now().strftime("%I:%M %p")})
                    st.rerun()

    # ── SCHEDULE PAGE ──
    elif st.session_state.rx_page == "Schedule":
        st.markdown('<div class="sec-title">📅 Dosage Schedule</div>', unsafe_allow_html=True)
        if not st.session_state.schedule:
            st.markdown('<div style="padding:2rem;text-align:center;border:1px dashed rgba(255,255,255,0.07);border-radius:16px;color:#475569">⚠️ No schedule found. Please upload and analyze a prescription first.</div>', unsafe_allow_html=True)
        else:
            time_icons = {"Morning":"🌅","Afternoon":"☀️","Evening":"🌆","Night":"🌙"}
            for med in st.session_state.schedule:
                times = med.get("times",[])
                if isinstance(times, str): times = [t.strip() for t in times.split(",")]
                badges = "".join([f'<span class="tbadge">{time_icons.get(t,"💊")} {t}</span>' for t in times])
                st.markdown(f"""
                <div class="med-pill-card">
                <h4>💊 {med.get("name","Unknown")}</h4>
                <div class="meta-grid">
                    <div class="meta-cell"><span>Dose</span><strong>{med.get("dose","—")}</strong></div>
                    <div class="meta-cell"><span>Duration</span><strong>{med.get("duration","—")}</strong></div>
                    <div class="meta-cell"><span>Instructions</span><strong>{med.get("instructions","—")}</strong></div>
                </div>
                <div>{badges}</div>
                </div>""", unsafe_allow_html=True)
