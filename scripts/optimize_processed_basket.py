from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.processed_basket_optimizer import (
    optimize_basket_cheapest_by_item,
    parse_items_arg,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Optimize a local processed JSONL shopping basket.")
    parser.add_argument("--date", required=True)
    parser.add_argument("--point-code", required=True)
    parser.add_argument("--items", required=True, help='Example: "米:1,洗頭水:2"')
    parser.add_argument("--processed-root", default=str(PROJECT_ROOT / "data" / "processed"))
    args = parser.parse_args()

    items = parse_items_arg(args.items)
    result = optimize_basket_cheapest_by_item(
        args.date,
        args.point_code,
        items,
        processed_root=Path(args.processed_root),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
