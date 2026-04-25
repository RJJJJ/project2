from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.processed_basket_optimizer import (
    optimize_basket,
    optimize_basket_cheapest_by_item,
    optimize_basket_cheapest_single_store,
    optimize_basket_cheapest_two_stores,
    parse_items_arg,
)
from services.plan_recommender import recommend_plan


def main() -> int:
    parser = argparse.ArgumentParser(description="Optimize a local processed JSONL shopping basket.")
    parser.add_argument("--date", required=True)
    parser.add_argument("--point-code", required=True)
    parser.add_argument("--items", required=True, help='Example: "米:1,洗頭水:2"')
    parser.add_argument(
        "--plan",
        choices=("cheapest_by_item", "single_store", "two_stores", "all"),
        default="all",
    )
    parser.add_argument("--convenience-threshold", type=float, default=5.0)
    parser.add_argument("--processed-root", default=str(PROJECT_ROOT / "data" / "processed"))
    args = parser.parse_args()

    items = parse_items_arg(args.items)
    processed_root = Path(args.processed_root)
    if args.plan == "cheapest_by_item":
        result = optimize_basket_cheapest_by_item(args.date, args.point_code, items, processed_root)
    elif args.plan == "single_store":
        result = optimize_basket_cheapest_single_store(args.date, args.point_code, items, processed_root)
    elif args.plan == "two_stores":
        result = optimize_basket_cheapest_two_stores(args.date, args.point_code, items, processed_root)
    else:
        result = optimize_basket(args.date, args.point_code, items, processed_root)
        result.update(recommend_plan(result["plans"], args.convenience_threshold))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
