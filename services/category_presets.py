from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATEGORY_PRESETS_PATH = PROJECT_ROOT / "config" / "category_presets.json"
DEFAULT_CATEGORIES = list(range(1, 19)) + [19]


def parse_categories(value: str | None) -> list[int]:
    if not value:
        return DEFAULT_CATEGORIES.copy()
    categories: list[int] = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            categories.extend(range(int(start), int(end) + 1))
        else:
            categories.append(int(part))
    return categories


def load_category_presets(config_path: str | Path | None = None) -> dict[str, list[int]]:
    path = Path(config_path) if config_path else DEFAULT_CATEGORY_PRESETS_PATH
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}
    presets: dict[str, list[int]] = {}
    for name, values in data.items():
        if isinstance(values, list):
            presets[str(name)] = [int(value) for value in values]
    return presets


def resolve_categories(
    categories: str | None = None,
    preset: str | None = None,
    presets_path: str | Path | None = None,
) -> list[int]:
    if categories:
        return parse_categories(categories)
    if preset:
        presets = load_category_presets(presets_path)
        if preset not in presets:
            available = ", ".join(sorted(presets)) or "none"
            raise ValueError(f"Unknown category preset: {preset}. Available presets: {available}")
        return presets[preset]
    return DEFAULT_CATEGORIES.copy()
