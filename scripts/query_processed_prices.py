from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.processed_price_query import get_prices_for_keyword


OUTPUT_FIELDS = [
    "product_oid",
    "product_name",
    "quantity",
    "category_name",
    "supermarket_oid",
    "supermarket_name",
    "price_mop",
    "discount",
    "distance_m",
    "matched_alias",
]


def project_row(row: dict[str, Any]) -> dict[str, Any]:
    return {field: row.get(field) for field in OUTPUT_FIELDS}


def main() -> int:
    parser = argparse.ArgumentParser(description="Query local processed Consumer Council price JSONL.")
    parser.add_argument("--date", required=True)
    parser.add_argument("--point-code", required=True)
    parser.add_argument("--keyword", required=True)
    parser.add_argument("--processed-root", default=str(PROJECT_ROOT / "data" / "processed"))
    args = parser.parse_args()

    rows = get_prices_for_keyword(
        args.date,
        args.point_code,
        args.keyword,
        processed_root=Path(args.processed_root),
    )
    print(json.dumps([project_row(row) for row in rows], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
