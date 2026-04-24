from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
            if isinstance(value, dict):
                rows.append(value)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate processed Consumer Council JSONL files.")
    parser.add_argument("--date", required=True)
    parser.add_argument("--point-code", required=True)
    parser.add_argument("--processed-root", default=str(PROJECT_ROOT / "data" / "processed"))
    args = parser.parse_args()

    point_dir = Path(args.processed_root) / args.date / args.point_code
    if not point_dir.exists():
        raise SystemExit(f"Processed point directory not found: {point_dir}")

    supermarket_rows = read_jsonl(point_dir / "supermarkets.jsonl")
    price_rows: list[dict[str, Any]] = []
    for path in sorted(point_dir.glob("category_*_prices.jsonl")):
        price_rows.extend(read_jsonl(path))

    duplicate_counter: Counter[tuple[Any, Any, Any]] = Counter()
    category_counter: Counter[Any] = Counter()
    for row in price_rows:
        duplicate_counter[(row.get("product_oid"), row.get("supermarket_oid"), row.get("category_id"))] += 1
        category_counter[row.get("category_id")] += 1

    duplicated = [
        {
            "product_oid": key[0],
            "supermarket_oid": key[1],
            "category_id": key[2],
            "count": count,
        }
        for key, count in duplicate_counter.items()
        if count > 1
    ]

    summary = {
        "date": args.date,
        "point_code": args.point_code,
        "supermarket_rows_count": len(supermarket_rows),
        "price_rows_count": len(price_rows),
        "rows_missing_product_oid": sum(1 for row in price_rows if row.get("product_oid") is None),
        "rows_missing_supermarket_oid": sum(1 for row in price_rows if row.get("supermarket_oid") is None),
        "rows_missing_price_mop": sum(1 for row in price_rows if row.get("price_mop") is None),
        "duplicated_product_oid_supermarket_oid_category_id": duplicated,
        "top_10_category_counts": [
            {"category_id": category_id, "count": count}
            for category_id, count in category_counter.most_common(10)
        ],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if duplicated else 0


if __name__ == "__main__":
    raise SystemExit(main())
