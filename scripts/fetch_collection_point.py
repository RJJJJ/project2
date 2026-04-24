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

from services.consumer_price_api import ConsumerPriceApi
from services.price_flattener import flatten_items_price_response, flatten_supermarkets_response


DEFAULT_CONFIG = PROJECT_ROOT / "config" / "collection_points.json"


def parse_categories(value: str | None) -> list[int]:
    if not value:
        return list(range(1, 19)) + [19]
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


def load_points(config_path: Path) -> list[dict[str, Any]]:
    return json.loads(config_path.read_text(encoding="utf-8"))


def find_point(points: list[dict[str, Any]], point_code: str) -> dict[str, Any]:
    for point in points:
        if point.get("point_code") == point_code:
            return point
    raise ValueError(f"Unknown point_code: {point_code}")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def count_products(data: dict[str, Any]) -> int:
    node = data.get("data") if isinstance(data.get("data"), dict) else data
    items = node.get("itemsPrice") if isinstance(node, dict) else []
    return len(items) if isinstance(items, list) else 0


def fetch_point(
    point: dict[str, Any],
    categories: list[int],
    run_date: str,
    client: ConsumerPriceApi | None = None,
) -> dict[str, Any]:
    client = client or ConsumerPriceApi()
    point_code = str(point["point_code"])
    lat = float(point["lat"])
    lng = float(point["lng"])
    dst = int(point.get("dst", 500))

    raw_dir = PROJECT_ROOT / "data" / "raw" / run_date / point_code
    processed_dir = PROJECT_ROOT / "data" / "processed" / run_date / point_code

    summary = {
        "points_processed": 1,
        "categories_processed": 0,
        "supermarkets_found": 0,
        "products_found": 0,
        "price_records_found": 0,
        "failed_requests": [],
    }

    for category_id in categories:
        try:
            data = client.fetch_by_condition(category_id, lat, lng, dst=dst)
            source_url = data.get("source_url") or client.build_url(category_id, lat, lng, dst=dst)

            if category_id == 19:
                raw_path = raw_dir / "supermarkets_category_19.json"
                processed_path = processed_dir / "supermarkets.jsonl"
                rows = flatten_supermarkets_response(data, point_code, source_url, dst)
                summary["supermarkets_found"] += len(rows)
            else:
                raw_path = raw_dir / f"category_{category_id}.json"
                processed_path = processed_dir / f"category_{category_id}_prices.jsonl"
                rows = flatten_items_price_response(data, point_code, category_id, source_url, dst)
                summary["products_found"] += count_products(data)
                summary["price_records_found"] += len(rows)

            write_json(raw_path, data)
            write_jsonl(processed_path, rows)
            summary["categories_processed"] += 1
        except Exception as exc:  # noqa: BLE001 - CLI batch should continue
            summary["failed_requests"].append(
                {
                    "point_code": point_code,
                    "category_id": category_id,
                    "error": repr(exc),
                }
            )

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Consumer Council prices for one collection point.")
    parser.add_argument("--point-code", required=True)
    parser.add_argument("--categories", default="1-18,19")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()

    point = find_point(load_points(Path(args.config)), args.point_code)
    summary = fetch_point(point, parse_categories(args.categories), args.date)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if summary["failed_requests"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
