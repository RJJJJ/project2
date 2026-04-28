from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.fetch_collection_point import load_points
from scripts.verify_full_category_point import resolve_latest_date
from services.sqlite_store import DEFAULT_DB_PATH, connect_db, import_processed_date, init_db

DEFAULT_CONFIG = PROJECT_ROOT / "config" / "collection_points.json"
DEFAULT_PROCESSED_ROOT = PROJECT_ROOT / "data" / "processed"


def run_import_processed_to_sqlite(
    *,
    date: str = "latest",
    max_points: int = 15,
    processed_root: Path = DEFAULT_PROCESSED_ROOT,
    config_path: Path = DEFAULT_CONFIG,
    db_path: Path = DEFAULT_DB_PATH,
) -> dict:
    resolved_date = resolve_latest_date(processed_root) if date == "latest" else date
    points = load_points(config_path)[:max_points]
    point_codes = [str(point.get("point_code")) for point in points]
    with connect_db(db_path) as conn:
        init_db(conn)
        result = import_processed_date(conn, resolved_date, point_codes, processed_root, points)
    return {
        "date": resolved_date,
        "db_path": str(db_path),
        "points_requested": len(points),
        "points_imported": result["points_imported"],
        "products_upserted": result["products_upserted"],
        "supermarkets_upserted": result["supermarkets_upserted"],
        "price_records_upserted": result["price_records_upserted"],
        "warnings": result["warnings"],
        "errors": result["errors"],
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Import processed JSONL data into a local SQLite foundation database.")
    parser.add_argument("--date", default="latest")
    parser.add_argument("--max-points", type=int, default=15)
    parser.add_argument("--processed-root", type=Path, default=DEFAULT_PROCESSED_ROOT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args(argv)

    summary = run_import_processed_to_sqlite(
        date=args.date,
        max_points=args.max_points,
        processed_root=args.processed_root,
        config_path=args.config,
        db_path=args.db_path,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
