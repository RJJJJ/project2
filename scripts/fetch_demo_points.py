from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from scripts.fetch_collection_point import DEFAULT_CONFIG, fetch_point, load_points
from services.category_presets import resolve_categories
from services.consumer_price_api import ConsumerPriceApi


def summarize_point(point: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "point_code": point.get("point_code"),
        "point_name": point.get("name"),
        "supermarkets_found": summary.get("supermarkets_found", 0),
        "products_found": summary.get("products_found", 0),
        "price_records_found": summary.get("price_records_found", 0),
        "failed_requests": summary.get("failed_requests", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch demo data for multiple collection points.")
    parser.add_argument("--max-points", type=int, default=5)
    parser.add_argument("--categories")
    parser.add_argument("--preset", default="demo_daily", choices=("demo_daily", "food_basic", "household", "all_basic"))
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()

    points = load_points(Path(args.config))[: args.max_points]
    categories = resolve_categories(args.categories, args.preset)
    client = ConsumerPriceApi()

    summaries = []
    for point in points:
        current = fetch_point(point, categories, args.date, client=client)
        summaries.append(summarize_point(point, current))

    print(json.dumps({"points": summaries}, ensure_ascii=False, indent=2))
    has_failures = any(point["failed_requests"] for point in summaries)
    return 1 if has_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
