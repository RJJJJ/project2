from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROCESSED_ROOT = PROJECT_ROOT / "data" / "processed"


def _point_dir(date: str, point_code: str, processed_root: Path | None = None) -> Path:
    root = processed_root or DEFAULT_PROCESSED_ROOT
    return root / date / point_code


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
            if isinstance(value, dict):
                rows.append(value)
    return rows


def load_supermarkets(
    date: str,
    point_code: str,
    processed_root: Path | None = None,
) -> list[dict[str, Any]]:
    return _read_jsonl(_point_dir(date, point_code, processed_root) / "supermarkets.jsonl")


def load_price_records(
    date: str,
    point_code: str,
    processed_root: Path | None = None,
) -> list[dict[str, Any]]:
    point_dir = _point_dir(date, point_code, processed_root)
    rows: list[dict[str, Any]] = []
    for path in sorted(point_dir.glob("category_*_prices.jsonl")):
        rows.extend(_read_jsonl(path))
    return rows


def load_all_processed_rows(
    date: str,
    point_code: str,
    processed_root: Path | None = None,
) -> dict[str, list[dict[str, Any]]]:
    return {
        "supermarkets": load_supermarkets(date, point_code, processed_root),
        "price_records": load_price_records(date, point_code, processed_root),
    }


def build_supermarket_lookup(
    date: str,
    point_code: str,
    processed_root: Path | None = None,
) -> dict[int, dict[str, Any]]:
    lookup: dict[int, dict[str, Any]] = {}
    for row in load_supermarkets(date, point_code, processed_root):
        supermarket_oid = row.get("supermarket_oid")
        if supermarket_oid is None:
            continue
        lookup[int(supermarket_oid)] = row
    return lookup
