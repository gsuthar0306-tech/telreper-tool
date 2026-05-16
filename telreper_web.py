import streamlit as st
import asyncio
import time
from pathlib import Path
from datetime import datetime
import sys

# Import from reper.py
try:
    from reper import TelReper, REASON_MAP, SESSIONS_DIR
except ImportError:
    st.error("❌ Could not import reper.py. Make sure both files are in the same folder.")
    st.stop()

st.set_page_config(page_title="TelReper Control Center", page_icon="🚨", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .main {background-color: #0e1117;}
    .stButton>button {border-radius: 8px; font-weight: bold; height: 3em;}
    .session-card {padding: 12px; border-radius: 8px; background: #262730; margin: 5px 0; border-left: 5px solid #00ff88;}
</style>
""", unsafe_allow_html=True)

# Session State
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'stats' not in st.session_state:
    st.session_state.stats = {"success": 0, "failed": 0, "flood": 0}

st.title("🚨 TelReper Control Center")
st.caption("Advanced Telegram Mass Reporter")

tabs = st.tabs(["📊 Dashboard", "👤 Account Manager", "⚙️ Settings"])

# ==================== DASHBOARD ====================
with tabs[0]:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🚀 Mass Reporting")
        target = st.text_input("Target Channel Username", placeholder="chut_ki_chudai", help="Without @")
        
        reason = st.selectbox("Report Reason", options=list(REASON_MAP.keys()), index=3)
        reports_per_acc = st.number_input("Reports per Account", min_value=1, max_value=30, value=8)
        
        col_a, col_b = st.columns(2)
        with col_a:
            max_concurrent = st.slider("Max Concurrent Accounts", 1, 10, 3)
        with col_b:
            min_delay = st.slider("Min Delay (seconds)", 2.0, 10.0, 3.5)

        if st.button("🚀 START MASS REPORTING", type="primary", use_container_width=True):
            if not target:
                st.error("Please enter target username")
            else:
                with st.spinner("Starting reporting..."):
                    try:
                        class WebArgs:
                            def __init__(self):
                                self.target = target.strip('@')
                                self.method = reason
                                self.reports = reports_per_acc
                                self.add_account = None
                                self.session = None
                                self.proxy_file = "proxies.txt"
                                self.max_concurrent = max_concurrent
                                self.min_delay = min_delay
                                self.max_delay = min_delay + 5
                                self.shuffle_accounts = True
                                self.api_id = 0
                                self.api_hash = "YOUR_API_HASH"

                        reporter = TelReper(WebArgs())
                        
                        st.session_state.logs = [f"[{datetime.now().strftime('%H:%M:%S')}] Started reporting @{target}"]
                        
                        sessions = list(SESSIONS_DIR.glob("*.session"))
                        if not sessions:
                            st.error("No accounts found! Add accounts first.")
                        else:
                            for session in sessions:
                                st.info(f"Processing account: {session.stem}")
                                try:
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                    loop.run_until_complete(reporter._report_task(session, target))
                                except Exception as e:
                                    st.warning(f"Account {session.stem} error: {e}")
                                finally:
                                    loop.close()
                                    time.sleep(1)
                            
                            st.success("✅ Reporting Completed!")
                            st.session_state.stats = reporter.stats
                            st.session_state.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Finished!")
                            
                    except Exception as e:
                        st.error(f"Error: {e}")

    with col2:
        st.subheader("📈 Live Statistics")
        c1, c2, c3 = st.columns(3)
        c1.metric("✅ Success", st.session_state.stats["success"])
        c2.metric("❌ Failed", st.session_state.stats["failed"])
        c3.metric("⏳ Flood", st.session_state.stats["flood"])

        st.subheader("📜 Logs")
        log_text = "\n".join(st.session_state.logs[-20:])  # Last 20 logs
        st.text_area("Live Logs", value=log_text, height=400, disabled=True)

# ==================== ACCOUNT MANAGER ====================
with tabs[1]:
    st.subheader("Add New Account")
    
    phone = st.text_input("Phone Number", placeholder="+919876543210")
    
    if st.button("➕ Add Account", type="primary"):
        if phone:
            with st.spinner("Adding account..."):
                try:
                    class AddArgs:
                        def __init__(self):
                            self.add_account = phone
                            self.api_id = 0
                            self.api_hash = "YOUR_API_HASH"
                    
                    reporter = TelReper(AddArgs())
                    asyncio.run(reporter.run())
                    st.success("Account added successfully!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to add account: {e}")
        else:
            st.warning("Enter phone number")

    st.subheader("Connected Accounts")
    sessions = list(SESSIONS_DIR.glob("*.session"))
    if sessions:
        for s in sessions:
            st.markdown(f"<div class='session-card'>✅ {s.stem}</div>", unsafe_allow_html=True)
    else:
        st.info("No accounts added yet.")

    if st.button("🗑️ Delete All Sessions"):
        for f in SESSIONS_DIR.glob("*.session"):
            f.unlink()
        st.success("All sessions deleted!")
        st.rerun()

# ==================== SETTINGS ====================
with tabs[2]:
    st.subheader("API Settings")
    api_id = st.number_input("API ID", value=0)
    api_hash = st.text_input("API Hash", value="YOUR_API_HASH", type="password")
    
    st.info("Proxy support is available in CLI version (proxies.txt)")

st.caption("⚠️ Use responsibly | Only for reporting real violations | Misuse may lead to account bans")
