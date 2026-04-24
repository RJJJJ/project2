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

from scripts.fetch_collection_point import DEFAULT_CONFIG, fetch_point, load_points, parse_categories
from services.consumer_price_api import ConsumerPriceApi


def merge_summary(total: dict[str, Any], current: dict[str, Any]) -> None:
    total["points_processed"] += current["points_processed"]
    total["categories_processed"] += current["categories_processed"]
    total["supermarkets_found"] += current["supermarkets_found"]
    total["products_found"] += current["products_found"]
    total["price_records_found"] += current["price_records_found"]
    total["failed_requests"].extend(current["failed_requests"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Consumer Council prices for all configured collection points.")
    parser.add_argument("--max-points", type=int)
    parser.add_argument("--categories", default="1-18,19")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()

    points = load_points(Path(args.config))
    if args.max_points is not None:
        points = points[: args.max_points]

    categories = parse_categories(args.categories)
    client = ConsumerPriceApi()
    summary: dict[str, Any] = {
        "points_processed": 0,
        "categories_processed": 0,
        "supermarkets_found": 0,
        "products_found": 0,
        "price_records_found": 0,
        "failed_requests": [],
    }

    for point in points:
        current = fetch_point(point, categories, args.date, client=client)
        merge_summary(summary, current)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if summary["failed_requests"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
