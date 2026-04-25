from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot.telegram_bot import run_bot


def load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(PROJECT_ROOT / ".env")


def main() -> int:
    load_env()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Missing TELEGRAM_BOT_TOKEN. Copy config/bot.example.env to .env and set your token.", file=sys.stderr)
        return 1

    default_point_code = os.getenv("DEFAULT_POINT_CODE", "p001")
    default_date = os.getenv("DEFAULT_DATE", "latest")
    run_bot(token, default_point_code=default_point_code, default_date=default_date)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
