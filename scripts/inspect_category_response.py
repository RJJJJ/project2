from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.consumer_api_client import ConsumerPriceApiClient


DEFAULT_LAT = 22.201633520793436
DEFAULT_LNG = 113.54888621017024
DEFAULT_DST = 400


def first_items(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("data", "items", "list", "rows", "result", "results"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
            if isinstance(value, dict):
                nested_items = first_items(value)
                if nested_items:
                    return nested_items
    return []


def display_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("cn", "zh", "name_cn", "name", "en"):
            if value.get(key):
                return str(value[key])
    return None


def load_or_fetch(category_id: int, lat: float, lng: float, dst: int, lang: str) -> Any:
    raw_path = Path("data/raw") / f"category_{category_id}.json"
    if raw_path.exists():
        return json.loads(raw_path.read_text(encoding="utf-8"))

    client = ConsumerPriceApiClient()
    return client.fetch_category(category_id, lat, lng, dst=dst, lang=lang)


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect one Consumer Council category JSON response.")
    parser.add_argument("--category", type=int, required=True)
    parser.add_argument("--lat", type=float, default=DEFAULT_LAT)
    parser.add_argument("--lng", type=float, default=DEFAULT_LNG)
    parser.add_argument("--dst", type=int, default=DEFAULT_DST)
    parser.add_argument("--lang", default="cn")
    args = parser.parse_args()

    data = load_or_fetch(args.category, args.lat, args.lng, args.dst, args.lang)
    items = first_items(data)

    category_name = None
    if items:
        category_name = display_name(items[0].get("category_name"))

    result = {
        "category_id": args.category,
        "category_name": category_name,
        "product_count": len(items),
        "products": [],
    }

    for item in items[:5]:
        supermarkets = item.get("supermarkets") if isinstance(item.get("supermarkets"), list) else []
        result["products"].append(
            {
                "product_oid": item.get("oid"),
                "product_name": display_name(item.get("name")),
                "quantity": item.get("quantity"),
                "category_id": item.get("category_id"),
                "category_name": display_name(item.get("category_name")),
                "supermarket_price_records": [
                    {
                        "supermarket_code": supermarket.get("supermarket_code"),
                        "price": supermarket.get("price"),
                        "discount": supermarket.get("discount"),
                        "flag": supermarket.get("flag"),
                    }
                    for supermarket in supermarkets[:3]
                    if isinstance(supermarket, dict)
                ],
            }
        )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
