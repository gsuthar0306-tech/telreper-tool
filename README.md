# TelReper - Telegram Report Helper

TelReper is a small Streamlit app for submitting legitimate Telegram reports from accounts that the user owns and logs in with OTP. It is built for client use on Windows with a simple browser interface.

## What It Does

- Adds Telegram accounts through OTP login.
- Supports Telegram report reasons such as spam, fake account, violence, child abuse, pornography, copyright, illegal drugs, personal details, geo-irrelevant, and other.
- Keeps session files and logs outside the project folder at `~/.telreper`.
- Shows live run statistics and saved logs.
- Exports a clean run summary for client records.
- Lets the user check session health and delete expired sessions.
- Adds evidence context such as message link, photo/image, video, PDF/document, audio, or other media notes.
- Provides a local web interface through Streamlit.

## Important Limits

This tool is for real policy violations only. It does not guarantee Telegram moderation action. A successful report count means Telegram accepted the API request from the account.

The app intentionally caps reports per account in `reper.py` with:

```python
MAX_REPORTS_PER_ACCOUNT = 3
```

Raising this too high can cause account bans and can become abusive.

## Requirements

- Windows, Linux, or macOS
- Python 3.10+
- Telegram API ID and API hash from `https://my.telegram.org/apps`
- At least one Telegram account that can receive OTP

## Install

```bash
pip install -r requirements.txt
```

## Run On Windows

Double-click:

```text
launch_telreper.bat
```

Or run manually:

```bash
streamlit run telreper_web.py
```

Then open:

```text
http://localhost:8501
```

## First Setup

1. Open the app.
2. Go to the `Setup` tab.
3. Enter the client's own Telegram API ID and API hash from `https://my.telegram.org/apps`.
4. Press `Test API Credentials`.
5. Go to `Accounts`.
6. Enter phone number, send OTP, verify OTP.
7. If Telegram asks for 2FA, tick the 2FA box and enter the account password.

Use the API credentials created at `https://my.telegram.org/apps`.

## Save API Credentials On Windows

The Setup tab shows PowerShell commands like this:

```powershell
[Environment]::SetEnvironmentVariable("TELEGRAM_API_ID", "123456", "User")
[Environment]::SetEnvironmentVariable("TELEGRAM_API_HASH", "your_hash", "User")
```

After running those commands, restart the terminal or app.

## Reporting

1. Go to `Reports`.
2. Enter a Telegram username or `t.me` link.
3. Select the correct reason.
4. Add a short factual comment.
5. Add evidence context when available, such as a Telegram message link or media/document notes.
6. Press `Submit Report`.
7. Go to `Logs` to view results or download a summary.

Telegram's report API used by this app does not upload photo/PDF files as attachments. Evidence fields are included in the report text and in the exported run summary.

## Where Data Is Stored

Session files:

```text
~/.telreper/sessions
```

Run logs:

```text
~/.telreper/logs
```

Do not share session files, API hashes, OTP codes, or 2FA passwords.

## CLI Usage

Show reasons:

```bash
python reper.py --reasons
```

Submit a report:

```bash
python reper.py -t targetusername -m other -r 1 --comment "This channel appears to violate Telegram rules."
```

Add account from CLI:

```bash
python reper.py -an +919876543210 --api-id 123456 --api-hash your_hash
```

## Client Delivery Checklist

- Run `pip install -r requirements.txt`.
- Start the app once with `launch_telreper.bat`.
- Test API credentials.
- Add one account with OTP.
- Run `Check Session Health`.
- Submit one test report to a valid target only if there is a real violation.
- Download the run summary from the `Logs` tab.

## Safety Notes

- Use accurate reasons only.
- Keep comments factual.
- Do not include OTPs, passwords, API hashes, or unrelated private data in comments.
- Revoke exposed sessions from Telegram Settings > Devices.
- Misuse may lead to account bans.
