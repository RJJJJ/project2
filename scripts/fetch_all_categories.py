from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.consumer_api_client import ConsumerPriceApiClient
from services.item_price_flattener import flatten_items_price_response


DEFAULT_LAT = 22.201633520793436
DEFAULT_LNG = 113.54888621017024
DEFAULT_DST = 400


def parse_category_ids(value: str | None) -> list[int]:
    if not value:
        return list(range(1, 19))
    ids: list[int] = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            ids.extend(range(int(start), int(end) + 1))
        else:
            ids.append(int(part))
    return ids


def extract_product_count(data: Any) -> int:
    if isinstance(data, list):
        return len([item for item in data if isinstance(item, dict)])
    if isinstance(data, dict):
        for key in ("data", "items", "list", "rows", "result", "results"):
            value = data.get(key)
            if isinstance(value, list):
                return len([item for item in value if isinstance(item, dict)])
            if isinstance(value, dict):
                nested_count = extract_product_count(value)
                if nested_count:
                    return nested_count
    return 0


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch and flatten Consumer Council supermarket price categories.")
    parser.add_argument("--categories", help="Category ids, e.g. 1,2,3 or 1-18. Defaults to 1-18.")
    parser.add_argument("--lat", type=float, default=DEFAULT_LAT)
    parser.add_argument("--lng", type=float, default=DEFAULT_LNG)
    parser.add_argument("--dst", type=int, default=DEFAULT_DST)
    parser.add_argument("--lang", default="cn")
    parser.add_argument("--raw-dir", default="data/raw")
    parser.add_argument("--processed-dir", default="data/processed")
    args = parser.parse_args()

    category_ids = parse_category_ids(args.categories)
    raw_dir = Path(args.raw_dir)
    processed_dir = Path(args.processed_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    client = ConsumerPriceApiClient()
    total_products = 0
    total_price_records = 0
    failed_categories: list[dict[str, str | int]] = []

    for index, category_id in enumerate(category_ids):
        if index:
            time.sleep(client.sleep_seconds)

        source_url = client.build_category_url(category_id, args.lat, args.lng, dst=args.dst, lang=args.lang)
        try:
            data = client.fetch_category(category_id, args.lat, args.lng, dst=args.dst, lang=args.lang)
            raw_path = raw_dir / f"category_{category_id}.json"
            raw_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

            flattened = flatten_items_price_response(data, source_url, args.lat, args.lng, args.dst)
            processed_path = processed_dir / f"category_{category_id}_flattened.jsonl"
            write_jsonl(processed_path, flattened)

            product_count = extract_product_count(data)
            total_products += product_count
            total_price_records += len(flattened)
            print(
                json.dumps(
                    {
                        "category_id": category_id,
                        "products": product_count,
                        "price_records": len(flattened),
                        "raw_file": str(raw_path),
                        "processed_file": str(processed_path),
                    },
                    ensure_ascii=False,
                )
            )
        except Exception as exc:  # noqa: BLE001 - batch fetch should keep going
            failed_categories.append({"category_id": category_id, "error": repr(exc)})
            print(json.dumps({"category_id": category_id, "error": repr(exc)}, ensure_ascii=False), file=sys.stderr)

    summary = {
        "total_categories": len(category_ids),
        "total_products": total_products,
        "total_price_records": total_price_records,
        "failed_categories": failed_categories,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if failed_categories else 0


if __name__ == "__main__":
    raise SystemExit(main())
