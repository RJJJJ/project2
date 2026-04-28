from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROCESSED_ROOT = PROJECT_ROOT / "data" / "processed"
PRICE_CATEGORY_IDS = list(range(1, 19))
EXPECTED_FILES = [f"category_{category_id}_prices.jsonl" for category_id in PRICE_CATEGORY_IDS] + ["supermarkets.jsonl"]


def resolve_latest_date(processed_root: Path) -> str:
    if not processed_root.exists():
        raise FileNotFoundError(f"Processed root does not exist: {processed_root}")
    dates = sorted(path.name for path in processed_root.iterdir() if path.is_dir())
    if not dates:
        raise FileNotFoundError(f"No processed date directories found under {processed_root}")
    return dates[-1]


def count_jsonl_rows(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                count += 1
    return count


def verify_full_category_point(*, date: str = "latest", point_code: str = "p001", processed_root: Path = DEFAULT_PROCESSED_ROOT) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    missing_files: list[str] = []
    resolved_date = date
    try:
        if date == "latest":
            resolved_date = resolve_latest_date(processed_root)
    except Exception as exc:  # noqa: BLE001 - CLI should emit JSON, not traceback
        errors.append(str(exc))

    point_dir = processed_root / resolved_date / point_code
    files: list[dict[str, Any]] = []
    if errors:
        for name in EXPECTED_FILES:
            files.append({"name": name, "exists": False, "rows": 0})
            missing_files.append(name)
    elif not point_dir.exists():
        errors.append(f"point directory missing: {point_dir}")
        for name in EXPECTED_FILES:
            files.append({"name": name, "exists": False, "rows": 0})
            missing_files.append(name)
    else:
        for name in EXPECTED_FILES:
            path = point_dir / name
            exists = path.exists()
            rows = count_jsonl_rows(path) if exists else 0
            files.append({"name": name, "exists": exists, "rows": rows})
            if not exists:
                missing_files.append(name)
            elif rows == 0:
                warnings.append(f"zero rows: {name}")

    return {
        "date": resolved_date,
        "point_code": point_code,
        "ok": not missing_files and not errors,
        "missing_files": missing_files,
        "warnings": warnings,
        "files": files,
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Verify one point has all category 1-18 price files plus supermarkets.jsonl.")
    parser.add_argument("--date", default="latest")
    parser.add_argument("--point-code", default="p001")
    parser.add_argument("--processed-root", type=Path, default=DEFAULT_PROCESSED_ROOT)
    args = parser.parse_args(argv)

    summary = verify_full_category_point(date=args.date, point_code=args.point_code, processed_root=args.processed_root)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
