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

## Usage

### 1. Add Accounts
```bash
python reper.py -an +919876543210
```

### 2. Start Mass Reporting
```bash
python reper.py -r 10 -t targetusername -m child_abuse
```

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

**Note:** Session files are now stored outside the repository at `~/.telreper/sessions` and logs at `~/.telreper/logs`. This keeps your repo safe for client delivery.

## Warning
- This tool is for reporting real violations (harassment, child abuse, spam, etc.)
- Misuse can lead to your accounts getting banned
- Telegram may temporarily or permanently ban accounts that report too aggressively
- Use at your own risk

Made with ❤️ for justice against hate accounts.
