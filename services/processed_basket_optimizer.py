from __future__ import annotations

from pathlib import Path
from typing import Any

from services.processed_price_query import get_prices_for_keyword


def parse_items_arg(items_arg: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for part in items_arg.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            keyword, quantity_text = part.split(":", 1)
            keyword = keyword.strip()
            quantity = int(quantity_text.strip())
        else:
            keyword = part
            quantity = 1
        if not keyword:
            continue
        items.append({"keyword": keyword, "quantity": quantity})
    return items


def optimize_basket_cheapest_by_item(
    date: str,
    point_code: str,
    items: list[dict[str, Any]],
    processed_root: Path | None = None,
) -> dict[str, Any]:
    optimized_items: list[dict[str, Any]] = []
    warnings: list[str] = []

    for item in items:
        keyword = str(item["keyword"])
        requested_quantity = int(item.get("quantity", 1))
        matches = [
            row
            for row in get_prices_for_keyword(date, point_code, keyword, processed_root)
            if row.get("price_mop") is not None
        ]

        if not matches:
            warnings.append(f"No price records found for keyword: {keyword}")
            continue

        cheapest = min(
            matches,
            key=lambda row: (
                float(row["price_mop"]),
                str(row.get("product_name") or ""),
                str(row.get("supermarket_name") or ""),
            ),
        )
        unit_price = float(cheapest["price_mop"])
        subtotal = unit_price * requested_quantity

        optimized_items.append(
            {
                "keyword": keyword,
                "requested_quantity": requested_quantity,
                "product_oid": cheapest.get("product_oid"),
                "product_name": cheapest.get("product_name"),
                "package_quantity": cheapest.get("quantity"),
                "category_name": cheapest.get("category_name"),
                "supermarket_oid": cheapest.get("supermarket_oid"),
                "supermarket_name": cheapest.get("supermarket_name"),
                "unit_price_mop": unit_price,
                "subtotal_mop": subtotal,
            }
        )

    estimated_total = sum(float(item["subtotal_mop"]) for item in optimized_items)
    return {
        "date": date,
        "point_code": point_code,
        "plan_type": "cheapest_by_item",
        "items": optimized_items,
        "estimated_total_mop": estimated_total,
        "warnings": warnings,
    }
