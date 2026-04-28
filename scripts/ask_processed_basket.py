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


def _humanize_warnings(warnings: list[str]) -> list[str]:
    human: list[str] = []
    for warning in warnings:
        text = str(warning)
        if text.startswith("No price records found for keyword:"):
            keyword = text.split("keyword:", 1)[1].split(".", 1)[0].strip()
            human.append(f"\u300c{keyword}\u300d\u66ab\u6642\u672a\u80fd\u5728\u8cc7\u6599\u4e2d\u627e\u5230\uff0c\u8acb\u8a66\u8a66\u8f38\u5165\u66f4\u5177\u9ad4\u540d\u7a31\u3002")
        elif "No single store" in text:
            human.append("\u6c92\u6709\u55ae\u4e00\u8d85\u5e02\u627e\u9f4a\u6240\u6709\u5546\u54c1\uff0c\u5df2\u5617\u8a66\u5176\u4ed6\u7d44\u5408\u3002")
        elif "No one-store or two-store" in text:
            human.append("\u6c92\u6709\u4e00\u81f3\u5169\u9593\u8d85\u5e02\u53ef\u627e\u9f4a\u6240\u6709\u5546\u54c1\uff0c\u5df2\u5148\u5217\u51fa\u627e\u5230\u5546\u54c1\u7684\u53c3\u8003\u50f9\u683c\u3002")
        else:
            human.append(text)
    return list(dict.fromkeys(human))


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
    result["warnings"] = _humanize_warnings(result.get("warnings", []))
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
