from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from services.plan_recommender import recommend_plan
from services.processed_basket_optimizer import optimize_basket
from services.shopping_text_parser import parse_shopping_text


def main() -> int:
    parser = argparse.ArgumentParser(description="Optimize a natural-language shopping basket.")
    parser.add_argument("--date", required=True)
    parser.add_argument("--point-code", required=True)
    parser.add_argument("--convenience-threshold", type=float, default=5.0)
    parser.add_argument("--processed-root", default=str(PROJECT_ROOT / "data" / "processed"))
    parser.add_argument("text")
    args = parser.parse_args()

    items = parse_shopping_text(args.text)
    result = optimize_basket(args.date, args.point_code, items, Path(args.processed_root))
    result["parsed_items"] = items
    result.update(recommend_plan(result["plans"], args.convenience_threshold))

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
