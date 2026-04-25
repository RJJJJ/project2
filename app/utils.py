from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from services.collection_point_resolver import PointResolutionError, resolve_point_code


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROCESSED_ROOT = PROJECT_ROOT / "data" / "processed"
DEMO_PROCESSED_ROOT = PROJECT_ROOT / "demo_data" / "processed"
DEFAULT_POINT_CODE = "p001"


def has_processed_data(processed_root: Path) -> bool:
    if not processed_root.exists():
        return False
    for date_dir in processed_root.iterdir():
        if not date_dir.is_dir():
            continue
        for point_dir in date_dir.iterdir():
            if point_dir.is_dir() and any(point_dir.glob("category_*_prices.jsonl")):
                return True
    return False


def get_processed_root() -> Path:
    env_root = os.getenv("PROCESSED_ROOT")
    if env_root:
        return Path(env_root)
    if has_processed_data(DEFAULT_PROCESSED_ROOT):
        return DEFAULT_PROCESSED_ROOT
    return DEMO_PROCESSED_ROOT


def latest_processed_date(processed_root: Path | None = None) -> str | None:
    root = processed_root or get_processed_root()
    if not root.exists():
        return None
    dates = [
        path.name
        for path in root.iterdir()
        if path.is_dir() and any(point_dir.is_dir() for point_dir in path.iterdir())
    ]
    return sorted(dates)[-1] if dates else None


def resolve_date(date: str = "latest", processed_root: Path | None = None) -> str:
    root = processed_root or get_processed_root()
    if date != "latest":
        return date
    latest = latest_processed_date(root)
    if not latest:
        raise HTTPException(status_code=404, detail=f"Processed data not found: {root}")
    return latest


def resolve_point_from_request(
    point_code: str | None = None,
    point_name: str | None = None,
    district: str | None = None,
) -> dict[str, Any]:
    try:
        if point_code or point_name or district:
            return resolve_point_code(point_code=point_code, point_name=point_name, district=district)
        return resolve_point_code(point_code=DEFAULT_POINT_CODE)
    except PointResolutionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def ensure_processed_data_exists(
    date: str,
    point_code: str,
    processed_root: Path | None = None,
) -> None:
    root = processed_root or get_processed_root()
    point_dir = root / date / point_code
    if not point_dir.exists() or not any(point_dir.glob("category_*_prices.jsonl")):
        raise HTTPException(
            status_code=404,
            detail=f"Processed data not found: date={date}, point_code={point_code}",
        )
