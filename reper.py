import argparse
import asyncio
import logging
import os
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlparse

try:
    from telethon import TelegramClient, errors
    from telethon.tl.functions.account import ReportPeerRequest
    from telethon.tl.functions.channels import JoinChannelRequest
    from telethon.tl.types import (
        InputReportReasonChildAbuse,
        InputReportReasonCopyright,
        InputReportReasonFake,
        InputReportReasonGeoIrrelevant,
        InputReportReasonIllegalDrugs,
        InputReportReasonOther,
        InputReportReasonPersonalDetails,
        InputReportReasonPornography,
        InputReportReasonSpam,
        InputReportReasonViolence,
    )
except ImportError:
    print("Missing dependencies. Run: pip install -r requirements.txt")
    sys.exit(1)


DATA_DIR = Path.home() / ".telreper"
SESSIONS_DIR = DATA_DIR / "sessions"
LOGS_DIR = DATA_DIR / "logs"
MAX_REPORTS_PER_ACCOUNT = 3

REASON_MAP = {
    "spam": InputReportReasonSpam(),
    "fake_account": InputReportReasonFake(),
    "violence": InputReportReasonViolence(),
    "child_abuse": InputReportReasonChildAbuse(),
    "pornography": InputReportReasonPornography(),
    "copyright": InputReportReasonCopyright(),
    "geoirrelevant": InputReportReasonGeoIrrelevant(),
    "illegal_drugs": InputReportReasonIllegalDrugs(),
    "personal_details": InputReportReasonPersonalDetails(),
    "other": InputReportReasonOther(),
}

REASON_LABELS = {
    "spam": "Spam",
    "fake_account": "Fake account or impersonation",
    "violence": "Violence",
    "child_abuse": "Child abuse",
    "pornography": "Pornography",
    "copyright": "Copyright",
    "geoirrelevant": "Geo-irrelevant",
    "illegal_drugs": "Illegal drugs",
    "personal_details": "Personal details",
    "other": "Other",
}


def normalize_target(value: str) -> str:
    target = (value or "").strip()
    target = target.replace("https://t.me/", "").replace("http://t.me/", "")
    target = target.replace("t.me/", "")
    target = target.lstrip("@").strip("/")
    if "/" in target:
        target = target.split("/", 1)[0]
    return target


def session_name_from_phone(phone: str) -> str:
    return phone.strip("+").replace(" ", "").replace("-", "")


def parse_proxy_url(proxy_url: str):
    value = (proxy_url or "").strip()
    if not value:
        return None

    parsed = urlparse(value)
    if parsed.scheme not in {"socks5", "socks4", "http"}:
        raise ValueError("Proxy must start with socks5://, socks4://, or http://")
    if not parsed.hostname or not parsed.port:
        raise ValueError("Proxy URL must include host and port.")

    proxy = {
        "proxy_type": parsed.scheme,
        "addr": parsed.hostname,
        "port": parsed.port,
        "rdns": True,
    }
    if parsed.username:
        proxy["username"] = parsed.username
    if parsed.password:
        proxy["password"] = parsed.password
    return proxy


class TelReper:
    def __init__(self, args):
        self.args = args
        self.proxies = self._load_proxies()
        self.proxy = parse_proxy_url(getattr(args, "proxy_url", ""))
        self.stats = {"success": 0, "failed": 0, "flood": 0}
        self._setup_dirs()
        self._setup_logging()

    def _setup_dirs(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        LOGS_DIR.mkdir(parents=True, exist_ok=True)

    def _setup_logging(self):
        log_file = LOGS_DIR / f"telreper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.latest_log_path = log_file
        self.logger = logging.getLogger(f"TelReper.{id(self)}")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        self.logger.handlers.clear()

        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(stream_handler)

    def _load_proxies(self) -> List[Dict]:
        proxy_file = Path(getattr(self.args, "proxy_file", "proxies.txt"))
        if not proxy_file.exists():
            return []
        return []

    def _client_for_session(self, session_path: Path) -> TelegramClient:
        return TelegramClient(
            str(session_path.with_suffix("")),
            self.args.api_id,
            self.args.api_hash,
            proxy=self.proxy,
        )

    async def add_account(self, phone: str):
        session_name = session_name_from_phone(phone)
        client = TelegramClient(str(SESSIONS_DIR / session_name), self.args.api_id, self.args.api_hash, proxy=self.proxy)
        print(f"Adding account: {phone}")
        try:
            await client.start(phone=phone)
            me = await client.get_me()
            print(f"Account added: {me.first_name}")
        except Exception as exc:
            print(f"Failed: {exc}")
        finally:
            await client.disconnect()

    async def request_code(self, phone: str) -> str:
        session_name = session_name_from_phone(phone)
        client = TelegramClient(str(SESSIONS_DIR / session_name), self.args.api_id, self.args.api_hash, proxy=self.proxy)
        await client.connect()
        try:
            sent = await client.send_code_request(phone)
            return sent.phone_code_hash
        finally:
            await client.disconnect()

    async def sign_in_with_code(self, phone: str, code: str, phone_code_hash: str, password: str = None) -> bool:
        session_name = session_name_from_phone(phone)
        client = TelegramClient(str(SESSIONS_DIR / session_name), self.args.api_id, self.args.api_hash, proxy=self.proxy)
        await client.connect()
        try:
            if await client.is_user_authorized():
                return True
            try:
                await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
            except errors.SessionPasswordNeededError:
                if not password:
                    raise
                await client.sign_in(password=password)
            return await client.is_user_authorized()
        finally:
            await client.disconnect()

    async def _report_task(self, session_path: Path, target: str):
        client = self._client_for_session(session_path)
        session_name = session_path.stem

        try:
            await client.connect()
            if not await client.is_user_authorized():
                self.logger.warning(f"[{session_name}] Invalid session. Delete this session and add the account again.")
                self.stats["failed"] += 1
                return

            me = await client.get_me()
            display_name = " ".join(part for part in [me.first_name, me.last_name] if part) or me.username or str(me.id)
            self.logger.info(f"[{session_name}] Using: {display_name}")

            clean_target = normalize_target(target)
            try:
                entity = await client.get_entity(clean_target)
            except (ValueError, errors.UsernameInvalidError, errors.UsernameNotOccupiedError):
                self.logger.error(
                    f"[{session_name}] Target not found: @{clean_target}. Check the username or paste a valid t.me link."
                )
                self.stats["failed"] += 1
                return

            try:
                await client(JoinChannelRequest(entity))
            except Exception:
                pass

            reason_key = getattr(self.args, "method", "other")
            reason = REASON_MAP.get(reason_key, REASON_MAP["other"])
            comment = getattr(self.args, "comment", "").strip()
            if not comment:
                comment = "This account/channel appears to violate Telegram rules."

            requested_reports = max(1, int(getattr(self.args, "reports", 1)))
            reports_to_send = min(requested_reports, MAX_REPORTS_PER_ACCOUNT)
            if requested_reports > MAX_REPORTS_PER_ACCOUNT:
                self.logger.warning(
                    f"[{session_name}] Capped reports per account at {MAX_REPORTS_PER_ACCOUNT} for responsible use."
                )

            min_delay = float(getattr(self.args, "min_delay", 3.0))
            max_delay = float(getattr(self.args, "max_delay", 9.0))
            if max_delay < min_delay:
                max_delay = min_delay

            for index in range(reports_to_send):
                try:
                    await client(ReportPeerRequest(peer=entity, reason=reason, message=comment))
                    self.stats["success"] += 1
                    self.logger.info(f"[{session_name}] Report {index + 1}/{reports_to_send} sent as {reason_key}")
                    await asyncio.sleep(random.uniform(min_delay, max_delay))
                except errors.FloodWaitError as exc:
                    self.logger.warning(f"[{session_name}] Flood wait: {exc.seconds}s")
                    self.stats["flood"] += 1
                    await asyncio.sleep(exc.seconds + 10)
                    break
                except Exception as exc:
                    self.logger.error(f"[{session_name}] Error: {exc}")
                    self.stats["failed"] += 1
                    await asyncio.sleep(5)

        except Exception as exc:
            self.logger.error(f"[{session_name}] Critical error: {exc}")
            self.stats["failed"] += 1
        finally:
            await client.disconnect()

    async def run(self):
        if getattr(self.args, "add_account", None):
            await self.add_account(self.args.add_account)
            return

        target = normalize_target(getattr(self.args, "target", ""))
        if not target:
            self.logger.error("Target required.")
            return

        sessions = sorted(SESSIONS_DIR.glob("*.session"))
        if getattr(self.args, "session", None):
            sessions = [SESSIONS_DIR / f"{self.args.session}.session"]

        if not sessions:
            self.logger.error("No sessions found.")
            return

        if getattr(self.args, "shuffle_accounts", True):
            random.shuffle(sessions)

        self.logger.info(f"=== TelReper started on @{target} ===")
        semaphore = asyncio.Semaphore(getattr(self.args, "max_concurrent", 3))

        async def worker(session_path):
            async with semaphore:
                await asyncio.sleep(random.uniform(1, 4))
                await self._report_task(session_path, target)

        await asyncio.gather(*(worker(session) for session in sessions))

        print("\n=== FINAL STATS ===")
        print(f"Success : {self.stats['success']}")
        print(f"Failed  : {self.stats['failed']}")
        print(f"Flood   : {self.stats['flood']}")
        print(f"Log     : {self.latest_log_path}")


def resolve_api_credentials(args):
    if args.api_id is None:
        env_api_id = os.getenv("TELEGRAM_API_ID")
        if env_api_id:
            try:
                args.api_id = int(env_api_id)
            except ValueError:
                args.api_id = None
    if args.api_hash is None:
        args.api_hash = os.getenv("TELEGRAM_API_HASH")
    return args


def main():
    parser = argparse.ArgumentParser(description="TelReper")
    parser.add_argument("-t", "--target")
    parser.add_argument("-m", "--method", default="other")
    parser.add_argument("-r", "--reports", type=int, default=1)
    parser.add_argument("--comment", default="")
    parser.add_argument("-an", "--add-account")
    parser.add_argument("-s", "--session")
    parser.add_argument("--proxy-file", default="proxies.txt")
    parser.add_argument("--proxy-url", default="")
    parser.add_argument("--max-concurrent", type=int, default=3)
    parser.add_argument("--min-delay", type=float, default=3.0)
    parser.add_argument("--max-delay", type=float, default=9.0)
    parser.add_argument("--shuffle-accounts", action="store_true", default=True)
    parser.add_argument("--api-id", type=int, default=None)
    parser.add_argument("--api-hash", default=None)
    parser.add_argument("--reasons", action="store_true", help="Show supported report reasons and exit.")

    args = parser.parse_args()
    if args.reasons:
        print("Supported report reasons:")
        for key, label in REASON_LABELS.items():
            print(f"  {key:<18} {label}")
        return

    if args.method not in REASON_MAP:
        print(f"Unknown report reason: {args.method}")
        print("Run `python reper.py --reasons` to see supported reasons.")
        sys.exit(1)

    args = resolve_api_credentials(args)
    if not args.api_id or not args.api_hash:
        print("Please set TELEGRAM_API_ID and TELEGRAM_API_HASH or pass --api-id and --api-hash.")
        sys.exit(1)

    app = TelReper(args)
    asyncio.run(app.run())


if __name__ == "__main__":
    main()
