# TelReper - Telegram Mass Reporter

Advanced Telegram channel reporting tool made for mass reporting abusive/hate channels.

---

## Features

- Add unlimited Telegram accounts
- Mass reporting with different reasons
- Automatic channel joining
- Flood wait handling
- Colored console output
- Logging support
- Simple and easy to use CLI

## Reasons Available

- `spam`
- `fake_account`
- `violence`
- `child_abuse` ← **Recommended for hate channels**
- `pornography`
- `geoirrelevant`

---

## Installation

1. Install requirements:
```bash
pip install -r requirements.txt
```

## Environment setup

This app requires your own Telegram API credentials.
Create them at https://my.telegram.org and set them as environment variables:

```bash
export TELEGRAM_API_ID=your_api_id
export TELEGRAM_API_HASH=your_api_hash
```

On Windows PowerShell:
```powershell
$env:TELEGRAM_API_ID="your_api_id"
$env:TELEGRAM_API_HASH="your_api_hash"
```

You can also enter these values in the Settings tab on the app.

## Usage

### 1. Add Accounts
```bash
python reper.py -an +919876543210 --api-id 123456 --api-hash your_hash
```

### 2. Start Mass Reporting
```bash
python reper.py -r 10 -t targetusername -m child_abuse
```
### 3. Run the Web App
```bash
streamlit run telreper_web.py
```

Then open `http://localhost:8501` in your browser.

### 4. Share with Cloudflare Tunnel (optional)
Install cloudflared, login, and forward the local port:

```bash
cloudflared login
cloudflared tunnel --url http://localhost:8501
```

This will give you a secure temporary URL to share with your client.
### Other Commands

**Show help:**
```bash
python reper.py --help
```

**Show all reasons:**
```bash
python reper.py --reasons
```

## Recommended Settings (For Best Results)
```bash
# For hate/abusive channels
python reper.py -r 8 -t targetusername -m child_abuse --max-concurrent 3
```

**Tips:**
- Use 5–15 reports per account
- Use `child_abuse` or `pornography` for faster action
- Don't use very high report count on single account
- Add many aged accounts for better effect
- Use proxies (advanced users)

## Project Structure
```text
telreper/
├── reper.py
├── requirements.txt
├── README.md
└── templates/
```

**Important Client Delivery Note:**
- Do not include any Telegram session files or logs in the repository.
- Session files are now stored outside the repo at `~/.telreper/sessions`.
- Logs are now stored at `~/.telreper/logs`.
- `.gitignore` already prevents `sessions/`, `logs/`, `*.session`, and `__pycache__/` from being committed.

If a session was previously exposed, revoke active Telegram sessions from Telegram Settings → Devices or re-login with a fresh account. This ensures old sessions cannot be reused.

## Warning
- This tool is for reporting real violations (harassment, child abuse, spam, etc.)
- Misuse can lead to your accounts getting banned
- Telegram may temporarily or permanently ban accounts that report too aggressively
- Use at your own risk

Made with ❤️ for justice against hate accounts.
