from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


REQUIRED_PACKAGES = [
    "fastapi",
    "uvicorn",
    "pydantic",
    "requests",
    "dotenv",
    "telegram",
]
DEFAULT_PROCESSED_ROOT = PROJECT_ROOT / "data" / "processed"
DEFAULT_POINT_CODE = "p001"


def _latest_processed_date(processed_root: Path = DEFAULT_PROCESSED_ROOT) -> str | None:
    if not processed_root.exists():
        return None
    dates = [path.name for path in processed_root.iterdir() if path.is_dir()]
    return sorted(dates)[-1] if dates else None


def _has_processed_data(date: str | None, point_code: str, processed_root: Path = DEFAULT_PROCESSED_ROOT) -> bool:
    if not date:
        return False
    point_dir = processed_root / date / point_code
    return point_dir.exists() and any(point_dir.glob("category_*_prices.jsonl"))


def _import_required_packages(errors: list[str]) -> bool:
    ok = True
    for package in REQUIRED_PACKAGES:
        try:
            importlib.import_module(package)
        except Exception as exc:  # noqa: BLE001 - diagnostic tool should report all missing imports.
            ok = False
            errors.append(f"Cannot import {package}: {exc}")
    return ok


def build_summary(project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    errors: list[str] = []
    processed_root = project_root / "data" / "processed"
    latest_processed_date = _latest_processed_date(processed_root)

    python_ok = sys.version_info >= (3, 10)
    if not python_ok:
        errors.append(f"Python 3.10+ required, current={sys.version.split()[0]}")

    packages_ok = _import_required_packages(errors)

    try:
        from services.collection_point_resolver import load_collection_points

        collection_points_count = len(load_collection_points(project_root / "config" / "collection_points.json"))
    except Exception as exc:  # noqa: BLE001 - diagnostic tool should continue.
        collection_points_count = 0
        errors.append(f"Cannot load collection points: {exc}")

    processed_data_ok = processed_root.exists() and _has_processed_data(
        latest_processed_date,
        DEFAULT_POINT_CODE,
        processed_root,
    )
    if not processed_root.exists():
        errors.append(f"Processed root not found: {processed_root}")
    elif not processed_data_ok:
        errors.append(f"No processed data found for {DEFAULT_POINT_CODE} at latest date")

    try:
        importlib.import_module("app.main")
        api_import_ok = True
    except Exception as exc:  # noqa: BLE001 - diagnostic tool should report import failure.
        api_import_ok = False
        errors.append(f"Cannot import FastAPI app: {exc}")

    frontend_ok = (project_root / "frontend" / "package.json").exists()
    if not frontend_ok:
        errors.append("frontend/package.json not found")

    return {
        "python_ok": python_ok,
        "packages_ok": packages_ok,
        "processed_data_ok": processed_data_ok,
        "latest_processed_date": latest_processed_date,
        "collection_points_count": collection_points_count,
        "api_import_ok": api_import_ok,
        "frontend_ok": frontend_ok,
        "errors": errors,
    }


def main() -> int:
    summary = build_summary()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not summary["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
