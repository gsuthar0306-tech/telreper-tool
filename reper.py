import asyncio
import random
import logging
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

try:
    from telethon import TelegramClient, errors
    from telethon.tl.functions.messages import ReportSpamRequest, ReportRequest
    from telethon.tl.functions.channels import JoinChannelRequest
    from telethon.tl.types import (
        InputReportReasonSpam, InputReportReasonFake, InputReportReasonViolence,
        InputReportReasonChildAbuse, InputReportReasonPornography,
        InputReportReasonGeoIrrelevant, InputReportReasonOther,
    )
    import colorama
    from colorama import Fore, Style
except ImportError:
    print("❌ Missing dependencies. Run: pip install telethon colorama")
    sys.exit(1)

colorama.init(autoreset=True)

SESSIONS_DIR = Path("sessions")
LOGS_DIR = Path("logs")

REASON_MAP = {
    "spam": InputReportReasonSpam(),
    "fake_account": InputReportReasonFake(),
    "violence": InputReportReasonViolence(),
    "child_abuse": InputReportReasonChildAbuse(),
    "pornography": InputReportReasonPornography(),
    "geoirrelevant": InputReportReasonGeoIrrelevant(),
    "other": InputReportReasonOther(),
}


class TelReper:
    def __init__(self, args):
        self.args = args
        self.proxies = self._load_proxies()
        self.stats = {"success": 0, "failed": 0, "flood": 0}
        self._setup_dirs()
        self._setup_logging()

    def _setup_dirs(self):
        SESSIONS_DIR.mkdir(exist_ok=True)
        LOGS_DIR.mkdir(exist_ok=True)

    def _setup_logging(self):
        log_file = LOGS_DIR / f"telreper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler(sys.stdout)]
        )
        self.logger = logging.getLogger("TelReper")

    def _load_proxies(self) -> List[Dict]:
        proxy_file = Path(getattr(self.args, 'proxy_file', 'proxies.txt'))
        if not proxy_file.exists():
            return []
        # Simple loading for now
        return []

    # ... (rest of the class remains same as previous version)

    async def add_account(self, phone: str):
        session_name = phone.strip("+").replace(" ", "")
        client = TelegramClient(str(SESSIONS_DIR / session_name), self.args.api_id, self.args.api_hash)
        print(f"\n{Fore.CYAN}Adding account: {phone}")
        try:
            await client.start(phone=phone)
            me = await client.get_me()
            print(f"{Fore.GREEN}✅ Account added: {me.first_name}")
        except Exception as e:
            print(f"{Fore.RED}❌ Failed: {e}")
        finally:
            await client.disconnect()

    async def _report_task(self, session_path: Path, target: str):
        proxy = None  # You can expand later
        client = TelegramClient(
            str(session_path.with_suffix("")),
            self.args.api_id,
            self.args.api_hash,
            proxy=proxy
        )

        session_name = session_path.stem
        try:
            await client.connect()
            if not await client.is_user_authorized():
                self.logger.warning(f"{Fore.RED}[{session_name}] Invalid session")
                self.stats["failed"] += 1
                return

            me = await client.get_me()
            self.logger.info(f"{Fore.BLUE}[{session_name}] Using: {me.first_name}")

            entity = await client.get_entity(target)

            try:
                await client(JoinChannelRequest(entity))
            except:
                pass

            messages = await client.get_messages(entity, limit=8)
            msg_ids = [m.id for m in messages if m.id] or [0]

            for i in range(self.args.reports):
                try:
                    if self.args.method == "spam":
                        await client(ReportSpamRequest(peer=entity))
                    else:
                        await client(ReportRequest(
                            peer=entity,
                            id=msg_ids,
                            option=b'',
                            message="Harassment, hate speech and vulgar content."
                        ))

                    self.stats["success"] += 1
                    self.logger.info(f"{Fore.GREEN}[{session_name}] ✅ Report {i+1}/{self.args.reports}")

                    await asyncio.sleep(random.uniform(3.0, 8.0))

                except errors.FloodWaitError as e:
                    self.logger.warning(f"{Fore.YELLOW}[{session_name}] Flood: {e.seconds}s")
                    self.stats["flood"] += 1
                    await asyncio.sleep(e.seconds + 10)
                    break
                except Exception as e:
                    self.logger.error(f"{Fore.RED}[{session_name}] Error: {e}")
                    self.stats["failed"] += 1
                    await asyncio.sleep(5)

        except Exception as e:
            self.logger.error(f"{Fore.RED}[{session_name}] Critical Error: {e}")
            self.stats["failed"] += 1
        finally:
            await client.disconnect()

    async def run(self):
        if getattr(self.args, 'add_account', None):
            await self.add_account(self.args.add_account)
            return

        if not getattr(self.args, 'target', None):
            self.logger.error("Target required!")
            return

        sessions = list(SESSIONS_DIR.glob("*.session"))
        if getattr(self.args, 'session', None):
            sessions = [SESSIONS_DIR / f"{self.args.session}.session"]

        if not sessions:
            self.logger.error("No sessions found!")
            return

        if getattr(self.args, 'shuffle_accounts', True):
            random.shuffle(sessions)

        self.logger.info(f"{Fore.MAGENTA}=== TelReper Started on @{self.args.target} ===")

        semaphore = asyncio.Semaphore(getattr(self.args, 'max_concurrent', 3))

        async def worker(s_path):
            async with semaphore:
                await asyncio.sleep(random.uniform(1, 4))
                await self._report_task(s_path, self.args.target)

        await asyncio.gather(*[worker(s) for s in sessions])

        print(f"\n{Style.BRIGHT}{Fore.WHITE}=== FINAL STATS ===")
        print(f"{Fore.GREEN}Success : {self.stats['success']}")
        print(f"{Fore.RED}Failed  : {self.stats['failed']}")
        print(f"{Fore.YELLOW}Flood   : {self.stats['flood']}")


def main():
    parser = argparse.ArgumentParser(description="TelReper")
    parser.add_argument("-t", "--target")
    parser.add_argument("-m", "--method", default="child_abuse")
    parser.add_argument("-r", "--reports", type=int, default=8)
    parser.add_argument("-an", "--add-account")
    parser.add_argument("-s", "--session")
    parser.add_argument("--proxy-file", default="proxies.txt")
    parser.add_argument("--max-concurrent", type=int, default=3)
    parser.add_argument("--min-delay", type=float, default=3.0)
    parser.add_argument("--max-delay", type=float, default=9.0)
    parser.add_argument("--shuffle-accounts", action="store_true", default=True)
    parser.add_argument("--api-id", type=int, default=0)
    parser.add_argument("--api-hash", default="YOUR_API_HASH")

    args = parser.parse_args()
    app = TelReper(args)
    asyncio.run(app.run())


if __name__ == "__main__":
    main()