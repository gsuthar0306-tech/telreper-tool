import streamlit as st
import asyncio
import time
from pathlib import Path
from datetime import datetime
import sys
from telethon import errors

# Import from reper.py
try:
    from reper import TelReper, REASON_MAP, SESSIONS_DIR
except ImportError:
    st.error("❌ Could not import reper.py. Make sure both files are in the same folder.")
    st.stop()

st.set_page_config(page_title="TelReper Control Center", page_icon="🚨", layout="wide")

COUNTRY_CODES = [
    ("🇮🇳 India", "+91"),
    ("🇺🇸 United States", "+1"),
    ("🇬🇧 United Kingdom", "+44"),
    ("🇵🇰 Pakistan", "+92"),
    ("🇧🇩 Bangladesh", "+880"),
    ("🇦🇺 Australia", "+61"),
    ("🇨🇦 Canada", "+1"),
    ("🇳🇬 Nigeria", "+234"),
    ("🇿🇦 South Africa", "+27"),
    ("🇦🇪 United Arab Emirates", "+971"),
]

# Custom CSS
st.markdown("""
<style>
    .main {background-color: #0e1117;}
    .stButton>button {border-radius: 8px; font-weight: bold; height: 3em;}
    .session-card {padding: 12px; border-radius: 8px; background: #262730; margin: 5px 0; border-left: 5px solid #00ff88;}
    .stAppViewContainer, .block-container {max-width: 1200px; margin: auto;}
    @media (max-width: 900px) {
        .stAppViewContainer, .block-container {padding-left: 0.75rem; padding-right: 0.75rem;}
        .stButton>button {width: 100%;}
    }
</style>
""", unsafe_allow_html=True)

# Session State
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'stats' not in st.session_state:
    st.session_state.stats = {"success": 0, "failed": 0, "flood": 0}
if 'auth_phone' not in st.session_state:
    st.session_state.auth_phone = ""
if 'auth_hash' not in st.session_state:
    st.session_state.auth_hash = ""
if 'awaiting_2fa' not in st.session_state:
    st.session_state.awaiting_2fa = False
if 'otp_requested' not in st.session_state:
    st.session_state.otp_requested = False
if 'otp_code' not in st.session_state:
    st.session_state.otp_code = ""
if 'auth_password' not in st.session_state:
    st.session_state.auth_password = ""
if 'api_id' not in st.session_state:
    st.session_state.api_id = 0
if 'api_hash' not in st.session_state:
    st.session_state.api_hash = "YOUR_API_HASH"


def run_async(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    else:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

st.title("🚨 TelReper Control Center")
st.caption("Advanced Telegram Mass Reporter")

tabs = st.tabs(["Account Manager", "Reports", "Settings"])

# ==================== REPORTS ====================
with tabs[1]:
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
                                self.api_id = st.session_state.api_id
                                self.api_hash = st.session_state.api_hash

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
with tabs[0]:
    st.subheader("Add New Account")
    st.markdown("Login first on this page, then go to Reports to file a report.")

    col_code, col_phone = st.columns([1, 2])
    country_code = col_code.text_input("Country Code", value="+91", help="Enter your country dialing code, for example +91.")
    phone_local = col_phone.text_input("Phone Number", placeholder="9876543210", help="Enter your phone number without the country code.")

    country_code = country_code.strip().replace(' ', '')
    if country_code and not country_code.startswith('+'):
        country_code = '+' + country_code

    phone = f"{country_code}{phone_local.strip().replace(' ', '')}" if phone_local else ""
    otp_code = st.text_input("OTP Code", placeholder="12345", key="otp_code", help="Enter the OTP sent by Telegram.")
    password = st.text_input("2FA Password", type="password", help="Enter your Telegram 2FA password only if your account has two-step verification enabled.")
    if not st.session_state.otp_requested:
        st.info("Press Send OTP to request the code, then enter it above and press Verify OTP.")

    send_col, verify_col = st.columns([1, 1])
    with send_col:
        if st.button("➕ Send OTP", type="primary", key="send_otp"):
            if not phone_local or not country_code:
                st.warning("Enter both country code and phone number.")
            else:
                with st.spinner("Requesting OTP..."):
                    try:
                        class AddArgs:
                            def __init__(self):
                                self.api_id = st.session_state.api_id
                                self.api_hash = st.session_state.api_hash

                        reporter = TelReper(AddArgs())
                        phone_code_hash = run_async(reporter.request_code(phone))
                        if not phone_code_hash:
                            raise Exception("Received no phone code hash from Telegram.")

                        st.session_state.auth_phone = phone
                        st.session_state.auth_hash = phone_code_hash
                        st.session_state.otp_requested = True
                        st.success("OTP sent. Enter the code above and press Verify OTP.")
                    except Exception as e:
                        st.error(f"Failed to request OTP: {e}")
    with verify_col:
        if st.button("✅ Verify OTP", type="primary", key="verify_otp"):
            if not st.session_state.otp_requested:
                st.warning("Request an OTP first before verifying.")
            elif not otp_code:
                st.warning("Enter the SMS code sent by Telegram.")
            else:
                with st.spinner("Verifying OTP..."):
                    try:
                        class AddArgs:
                            def __init__(self):
                                self.api_id = st.session_state.api_id
                                self.api_hash = st.session_state.api_hash

                        reporter = TelReper(AddArgs())
                        success = run_async(reporter.sign_in_with_code(
                            st.session_state.auth_phone,
                            otp_code,
                            st.session_state.auth_hash,
                            password if password else None
                        ))

                        if success:
                            st.success("Account added successfully!")
                            st.session_state.auth_phone = ""
                            st.session_state.auth_hash = ""
                            st.session_state.otp_requested = False
                            st.session_state.otp_code = ""
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("OTP verification failed. Please try again.")
                    except errors.SessionPasswordNeededError:
                        st.warning("This account requires a 2FA password. Enter it above and press Verify OTP again.")
                        st.session_state.awaiting_2fa = True
                    except Exception as e:
                        st.error(f"Failed to verify OTP: {e}")

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
    st.number_input("API ID", key="api_id")
    st.text_input("API Hash", type="password", key="api_hash")
    
    st.info("Proxy support is available in CLI version (proxies.txt)")

st.caption("⚠️ Use responsibly | Only for reporting real violations | Misuse may lead to account bans")
