import asyncio
import os
import re
import time
from datetime import datetime
from pathlib import Path

import streamlit as st
from telethon import TelegramClient, errors
from telethon.sessions import StringSession

try:
    from reper import (
        TelReper,
        REASON_MAP,
        REASON_LABELS,
        SESSIONS_DIR,
        LOGS_DIR,
        MAX_REPORTS_PER_ACCOUNT,
        normalize_target,
    )
except ImportError:
    st.error("Could not import reper.py. Keep telreper_web.py and reper.py in the same folder.")
    st.stop()


st.set_page_config(page_title="TelReper Control Center", page_icon="TR", layout="wide")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
DEFAULT_API_ID = None
DEFAULT_API_HASH = os.getenv("TELEGRAM_API_HASH") or ""
env_api_id = os.getenv("TELEGRAM_API_ID")
if env_api_id:
    try:
        DEFAULT_API_ID = int(env_api_id)
    except ValueError:
        DEFAULT_API_ID = None


st.markdown(
    """
<style>
    .block-container {max-width: 1180px; padding-top: 1.5rem;}
    .stButton>button {border-radius: 8px; font-weight: 650; min-height: 2.8rem;}
    .session-card {
        padding: 10px 12px;
        border-radius: 8px;
        background: #20232b;
        border-left: 4px solid #3ddc84;
        margin: 3px 0 10px 0;
    }
    .muted-box {
        padding: 12px;
        border-radius: 8px;
        background: #20232b;
        border: 1px solid rgba(255,255,255,0.08);
    }
    textarea {font-family: ui-monospace, SFMono-Regular, Consolas, monospace;}
</style>
""",
    unsafe_allow_html=True,
)


DEFAULT_STATE = {
    "logs": [],
    "stats": {"success": 0, "failed": 0, "flood": 0},
    "last_log_path": "",
    "last_summary": "",
    "auth_phone": "",
    "auth_hash": "",
    "awaiting_2fa": False,
    "otp_requested": False,
    "otp_code": "",
    "api_id": DEFAULT_API_ID or 0,
    "api_hash": DEFAULT_API_HASH,
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


def api_credentials_valid() -> bool:
    return bool(st.session_state.api_id and st.session_state.api_hash)


def run_async(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def read_recent_log_lines(path, limit=120):
    if not path:
        return []
    log_path = Path(path)
    if not log_path.exists():
        return []
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
    return [ANSI_RE.sub("", line) for line in lines]


def delete_session_files(session_path):
    for path in session_path.parent.glob(f"{session_path.stem}.session*"):
        path.unlink(missing_ok=True)


def build_summary(target, reason, comment, sessions, stats, log_path, log_lines):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "TelReper Run Summary",
        f"Generated: {now}",
        f"Target: @{target}",
        f"Reason: {REASON_LABELS.get(reason, reason)}",
        f"Accounts attempted: {len(sessions)}",
        f"Success: {stats['success']}",
        f"Failed: {stats['failed']}",
        f"Flood waits: {stats['flood']}",
        f"Log file: {log_path}",
        "",
        "Comment:",
        comment.strip() or "No comment provided.",
        "",
        "Recent log:",
        *log_lines[-80:],
    ]
    return "\n".join(lines)


async def test_api_credentials(api_id, api_hash):
    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.connect()
    try:
        return client.is_connected()
    finally:
        await client.disconnect()


async def check_session(session_path, api_id, api_hash):
    client = TelegramClient(str(session_path.with_suffix("")), api_id, api_hash)
    await client.connect()
    try:
        if not await client.is_user_authorized():
            return "Invalid", "Needs OTP login again"
        me = await client.get_me()
        name = " ".join(part for part in [me.first_name, me.last_name] if part)
        return "Ready", name or me.username or str(me.id)
    except Exception as exc:
        return "Error", str(exc)
    finally:
        await client.disconnect()


def make_args(**values):
    class Args:
        pass

    args = Args()
    for key, value in values.items():
        setattr(args, key, value)
    return args


st.title("TelReper Control Center")
st.caption("Client-ready Telegram report helper for legitimate policy violations.")

tabs = st.tabs(["Setup", "Accounts", "Reports", "Logs"])


with tabs[0]:
    st.subheader("API Setup")
    st.markdown(
        "Enter the Telegram API ID and API hash from `https://my.telegram.org/apps`."
    )

    st.number_input("Telegram API ID", key="api_id", min_value=0, step=1)
    st.text_input("Telegram API Hash", type="password", key="api_hash")

    setup_cols = st.columns([1, 1])
    with setup_cols[0]:
        if st.button("Test API Credentials", use_container_width=True):
            if not api_credentials_valid():
                st.warning("Enter API ID and API hash first.")
            else:
                try:
                    ok = run_async(test_api_credentials(st.session_state.api_id, st.session_state.api_hash))
                    if ok:
                        st.success("API credentials connected successfully.")
                    else:
                        st.error("Could not connect with these API credentials.")
                except Exception as exc:
                    st.error(f"API test failed: {exc}")

    with setup_cols[1]:
        st.info(f"Sessions: {SESSIONS_DIR}")
        st.info(f"Logs: {LOGS_DIR}")

    st.markdown("PowerShell command to save credentials for this Windows user:")
    api_id_value = st.session_state.api_id or "YOUR_API_ID"
    api_hash_value = st.session_state.api_hash or "YOUR_API_HASH"
    st.code(
        f'[Environment]::SetEnvironmentVariable("TELEGRAM_API_ID", "{api_id_value}", "User")\n'
        f'[Environment]::SetEnvironmentVariable("TELEGRAM_API_HASH", "{api_hash_value}", "User")',
        language="powershell",
    )


with tabs[1]:
    st.subheader("Account Login")
    st.markdown("Login is OTP-first. The 2FA password is needed only when Telegram asks for it.")

    phone_cols = st.columns([1, 2])
    country_code = phone_cols[0].text_input("Country Code", value="+91")
    phone_local = phone_cols[1].text_input("Phone Number", placeholder="9876543210")
    country_code = country_code.strip().replace(" ", "")
    if country_code and not country_code.startswith("+"):
        country_code = f"+{country_code}"
    phone = f"{country_code}{phone_local.strip().replace(' ', '')}" if phone_local else ""

    otp_code = st.text_input("OTP Code", placeholder="12345", key="otp_code")
    has_2fa = st.checkbox("Telegram asked for a 2FA password", value=st.session_state.awaiting_2fa)
    password = st.text_input("2FA Password", type="password") if has_2fa else ""

    login_cols = st.columns([1, 1])
    with login_cols[0]:
        if st.button("Send OTP", type="primary", use_container_width=True):
            if not api_credentials_valid():
                st.warning("Enter API credentials on the Setup tab first.")
            elif not phone:
                st.warning("Enter a full phone number.")
            else:
                try:
                    reporter = TelReper(make_args(api_id=st.session_state.api_id, api_hash=st.session_state.api_hash))
                    phone_code_hash = run_async(reporter.request_code(phone))
                    st.session_state.auth_phone = phone
                    st.session_state.auth_hash = phone_code_hash
                    st.session_state.otp_requested = True
                    st.session_state.awaiting_2fa = False
                    st.success("OTP sent. Enter the code and press Verify OTP.")
                except Exception as exc:
                    st.error(f"Failed to request OTP: {exc}")

    with login_cols[1]:
        if st.button("Verify OTP", type="primary", use_container_width=True):
            if not api_credentials_valid():
                st.warning("Enter API credentials on the Setup tab first.")
            elif not st.session_state.otp_requested:
                st.warning("Send OTP first.")
            elif not otp_code:
                st.warning("Enter the OTP code.")
            else:
                try:
                    reporter = TelReper(make_args(api_id=st.session_state.api_id, api_hash=st.session_state.api_hash))
                    success = run_async(
                        reporter.sign_in_with_code(
                            st.session_state.auth_phone,
                            otp_code,
                            st.session_state.auth_hash,
                            password or None,
                        )
                    )
                    if success:
                        st.success("Account added successfully.")
                        st.session_state.auth_phone = ""
                        st.session_state.auth_hash = ""
                        st.session_state.otp_requested = False
                        st.session_state.awaiting_2fa = False
                        st.session_state.otp_code = ""
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("OTP verification failed.")
                except errors.SessionPasswordNeededError:
                    st.session_state.awaiting_2fa = True
                    st.warning("Telegram requires this account's 2FA password.")
                except Exception as exc:
                    st.error(f"Failed to verify OTP: {exc}")

    st.divider()
    st.subheader("Connected Sessions")
    sessions = sorted(SESSIONS_DIR.glob("*.session"))

    health_cols = st.columns([1, 1])
    with health_cols[0]:
        run_health = st.button("Check Session Health", use_container_width=True)
    with health_cols[1]:
        confirm_delete_all = st.checkbox("Confirm deleting all sessions")

    if not sessions:
        st.info("No accounts added yet.")
    else:
        for session in sessions:
            status = ""
            detail = ""
            if run_health and api_credentials_valid():
                with st.spinner(f"Checking {session.stem}..."):
                    status, detail = run_async(check_session(session, st.session_state.api_id, st.session_state.api_hash))

            row = st.columns([3, 2, 1])
            row[0].markdown(f"<div class='session-card'>Account session: {session.stem}</div>", unsafe_allow_html=True)
            if status:
                row[1].write(f"{status}: {detail}")
            if row[2].button("Delete", key=f"delete_session_{session.stem}"):
                delete_session_files(session)
                st.success(f"Deleted {session.stem}. Add it again with OTP.")
                st.rerun()

    if st.button("Delete All Sessions"):
        if not confirm_delete_all:
            st.warning("Tick the confirmation box before deleting all sessions.")
        else:
            for session_file in SESSIONS_DIR.glob("*.session*"):
                session_file.unlink()
            st.success("All sessions deleted.")
            st.rerun()


with tabs[2]:
    st.subheader("Submit Report")
    target = st.text_input("Target Username or t.me Link", placeholder="example_channel or https://t.me/example_channel")
    reason = st.selectbox(
        "Report Reason",
        options=list(REASON_MAP.keys()),
        format_func=lambda key: REASON_LABELS.get(key, key.replace("_", " ").title()),
        index=list(REASON_MAP.keys()).index("other"),
    )
    comment = st.text_area(
        "Report Comment",
        value="This account/channel appears to violate Telegram rules.",
        help="Keep it factual. Do not include OTPs, passwords, API hashes, or unrelated private data.",
    )

    run_cols = st.columns([1, 1, 1])
    reports_per_acc = run_cols[0].number_input(
        "Reports per Account",
        min_value=1,
        max_value=MAX_REPORTS_PER_ACCOUNT,
        value=1,
        help=f"Maximum {MAX_REPORTS_PER_ACCOUNT} per account.",
    )
    max_concurrent = run_cols[1].slider("Concurrent Accounts", 1, 3, 1)
    min_delay = run_cols[2].slider("Min Delay Seconds", 2.0, 10.0, 3.5)

    if st.button("Submit Report", type="primary", use_container_width=True):
        clean_target = normalize_target(target)
        sessions = sorted(SESSIONS_DIR.glob("*.session"))

        if not clean_target:
            st.error("Enter a Telegram username or t.me link.")
        elif not api_credentials_valid():
            st.error("Enter API credentials on the Setup tab first.")
        elif not sessions:
            st.error("No accounts found. Add an account on the Accounts tab first.")
        else:
            args = make_args(
                target=clean_target,
                method=reason,
                reports=reports_per_acc,
                comment=comment,
                add_account=None,
                session=None,
                proxy_file="proxies.txt",
                max_concurrent=max_concurrent,
                min_delay=min_delay,
                max_delay=min_delay + 5,
                shuffle_accounts=True,
                api_id=st.session_state.api_id,
                api_hash=st.session_state.api_hash,
            )
            reporter = TelReper(args)
            st.session_state.last_log_path = str(reporter.latest_log_path)
            st.session_state.logs = [f"[{datetime.now().strftime('%H:%M:%S')}] Started report for @{clean_target}"]

            progress = st.progress(0)
            status = st.empty()
            for index, session in enumerate(sessions, start=1):
                status.info(f"Processing account {index}/{len(sessions)}: {session.stem}")
                try:
                    run_async(reporter._report_task(session, clean_target))
                except Exception as exc:
                    st.warning(f"Account {session.stem} error: {exc}")
                progress.progress(index / len(sessions))
                time.sleep(0.5)

            log_lines = read_recent_log_lines(reporter.latest_log_path)
            st.session_state.stats = reporter.stats
            st.session_state.logs = log_lines
            st.session_state.last_summary = build_summary(
                clean_target,
                reason,
                comment,
                sessions,
                reporter.stats,
                reporter.latest_log_path,
                log_lines,
            )
            status.success("Report run finished.")
            st.success("Finished. Check the Logs tab for details and export.")

    st.caption("Success means Telegram accepted the API request. It does not guarantee moderation action.")


with tabs[3]:
    st.subheader("Run Logs and Export")
    stats = st.session_state.stats
    metric_cols = st.columns(3)
    metric_cols[0].metric("Success", stats["success"])
    metric_cols[1].metric("Failed", stats["failed"])
    metric_cols[2].metric("Flood Waits", stats["flood"])

    if st.session_state.last_log_path:
        st.caption(f"Saved log: {st.session_state.last_log_path}")

    log_text = "\n".join(st.session_state.logs[-120:])
    st.text_area("Recent Log", value=log_text, height=360, disabled=True)

    export_cols = st.columns([1, 1])
    export_cols[0].download_button(
        "Download Run Summary",
        data=st.session_state.last_summary or "No run summary available yet.",
        file_name=f"telreper_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        mime="text/plain",
        use_container_width=True,
    )
    export_cols[1].download_button(
        "Download Raw Log",
        data=log_text or "No log available yet.",
        file_name=f"telreper_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        mime="text/plain",
        use_container_width=True,
    )

st.caption("Use responsibly. Report only real policy violations. Keep API credentials and session files private.")
