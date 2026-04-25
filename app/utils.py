from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import HTTPException

from services.collection_point_resolver import PointResolutionError, resolve_point_code


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROCESSED_ROOT = PROJECT_ROOT / "data" / "processed"
DEFAULT_POINT_CODE = "p001"


def latest_processed_date(processed_root: Path = DEFAULT_PROCESSED_ROOT) -> str | None:
    if not processed_root.exists():
        return None
    dates = [
        path.name
        for path in processed_root.iterdir()
        if path.is_dir() and any(point_dir.is_dir() for point_dir in path.iterdir())
    ]
    return sorted(dates)[-1] if dates else None


def resolve_date(date: str = "latest", processed_root: Path = DEFAULT_PROCESSED_ROOT) -> str:
    if date != "latest":
        return date
    latest = latest_processed_date(processed_root)
    if not latest:
        raise HTTPException(status_code=404, detail=f"Processed data not found: {processed_root}")
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
    processed_root: Path = DEFAULT_PROCESSED_ROOT,
) -> None:
    point_dir = processed_root / date / point_code
    if not point_dir.exists() or not any(point_dir.glob("category_*_prices.jsonl")):
        raise HTTPException(
            status_code=404,
            detail=f"Processed data not found: date={date}, point_code={point_code}",
        )

