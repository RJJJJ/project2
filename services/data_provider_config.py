from __future__ import annotations

import os
from pathlib import Path

from services.sqlite_store import DEFAULT_DB_PATH


def get_data_provider() -> str:
    provider = os.getenv("PROJECT2_DATA_PROVIDER", "jsonl").strip().casefold()
    return provider if provider in {"jsonl", "sqlite"} else "jsonl"


def get_sqlite_db_path() -> Path:
    return Path(os.getenv("PROJECT2_SQLITE_DB_PATH", str(DEFAULT_DB_PATH)))


def is_sqlite_provider_enabled() -> bool:
    return get_data_provider() == "sqlite"
