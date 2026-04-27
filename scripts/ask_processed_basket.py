from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from services.basket_text_formatter import format_basket_text
from services.collection_point_resolver import PointResolutionError, resolve_point_code
from services.plan_recommender import recommend_plan
from services.processed_basket_optimizer import optimize_basket
from services.shopping_text_parser import parse_shopping_text


def build_result(
    date: str,
    point_code: str,
    text: str,
    processed_root: Path,
    selected_products: list[dict[str, Any]] | None = None,
    convenience_threshold: float = 5.0,
) -> dict[str, Any]:
    items = parse_shopping_text(text)
    if selected_products:
        selected_by_keyword = {
            str(item.get("keyword")): item.get("product_oid")
            for item in selected_products
            if item.get("keyword") and item.get("product_oid") is not None
        }
        for item in items:
            selected_product_oid = selected_by_keyword.get(str(item.get("keyword")))
            if selected_product_oid is not None:
                item["selected_product_oid"] = selected_product_oid
    result = optimize_basket(date, point_code, items, processed_root)
    result["parsed_items"] = items
    result.update(recommend_plan(result["plans"], convenience_threshold))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Optimize a natural-language shopping basket.")
    parser.add_argument("--date", required=True)
    parser.add_argument("--point-code")
    parser.add_argument("--point-name")
    parser.add_argument("--district")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    parser.add_argument("--convenience-threshold", type=float, default=5.0)
    parser.add_argument("--processed-root", default=str(PROJECT_ROOT / "data" / "processed"))
    parser.add_argument("text")
    args = parser.parse_args()

    try:
        point = resolve_point_code(args.point_code, args.point_name, args.district)
    except PointResolutionError as exc:
        parser.error(str(exc))

    point_code = str(point["point_code"])
    result = build_result(
        args.date,
        point_code,
        args.text,
        Path(args.processed_root),
        args.convenience_threshold,
    )

    if args.format == "text":
        print(format_basket_text(result, args.text, point))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
