from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ALIASES_PATH = PROJECT_ROOT / "config" / "product_aliases.json"


def load_aliases(config_path: str | Path | None = None) -> dict[str, list[str]]:
    path = Path(config_path) if config_path else DEFAULT_ALIASES_PATH
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    aliases: dict[str, list[str]] = {}
    if not isinstance(data, dict):
        return aliases
    for keyword, values in data.items():
        if isinstance(values, list):
            aliases[str(keyword)] = [str(value) for value in values if str(value).strip()]
    return aliases


def expand_keyword(keyword: str, config_path: str | Path | None = None) -> list[str]:
    aliases = load_aliases(config_path)
    normalized = keyword.strip()
    if normalized in aliases:
        return aliases[normalized]
    return [normalized]
