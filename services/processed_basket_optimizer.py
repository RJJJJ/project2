from __future__ import annotations

from itertools import combinations
from pathlib import Path
from typing import Any

from services.processed_price_query import get_prices_for_keyword
from services.product_aliases import expand_keyword


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


def _priced_matches(
    date: str,
    point_code: str,
    keyword: str,
    processed_root: Path | None = None,
) -> list[dict[str, Any]]:
    return [
        row
        for row in get_prices_for_keyword(date, point_code, keyword, processed_root)
        if row.get("price_mop") is not None and row.get("supermarket_oid") is not None
    ]


def _build_plan_item(keyword: str, requested_quantity: int, row: dict[str, Any]) -> dict[str, Any]:
    unit_price = float(row["price_mop"])
    return {
        "keyword": keyword,
        "matched_alias": row.get("matched_alias"),
        "requested_quantity": requested_quantity,
        "product_oid": row.get("product_oid"),
        "product_name": row.get("product_name"),
        "package_quantity": row.get("quantity"),
        "category_name": row.get("category_name"),
        "supermarket_oid": row.get("supermarket_oid"),
        "supermarket_name": row.get("supermarket_name"),
        "unit_price_mop": unit_price,
        "subtotal_mop": unit_price * requested_quantity,
    }


def _stores_from_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    stores: dict[Any, dict[str, Any]] = {}
    for item in items:
        supermarket_oid = item.get("supermarket_oid")
        if supermarket_oid is None:
            continue
        stores[supermarket_oid] = {
            "supermarket_oid": supermarket_oid,
            "supermarket_name": item.get("supermarket_name"),
        }
    return list(stores.values())


def _plan_total(items: list[dict[str, Any]]) -> float:
    return sum(float(item["subtotal_mop"]) for item in items)


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
        matches = _priced_matches(date, point_code, keyword, processed_root)

        if not matches:
            aliases = expand_keyword(keyword)
            warnings.append(
                f"No price records found for keyword: {keyword}. Tried aliases: {', '.join(aliases)}"
            )
            continue

        cheapest = min(
            matches,
            key=lambda row: (
                float(row["price_mop"]),
                str(row.get("product_name") or ""),
                str(row.get("supermarket_name") or ""),
            ),
        )
        optimized_items.append(_build_plan_item(keyword, requested_quantity, cheapest))

    estimated_total = _plan_total(optimized_items)
    return {
        "date": date,
        "point_code": point_code,
        "plan_type": "cheapest_by_item",
        "store_count": len(_stores_from_items(optimized_items)),
        "stores": _stores_from_items(optimized_items),
        "items": optimized_items,
        "estimated_total_mop": estimated_total,
        "warnings": warnings,
    }


def _candidate_rows_by_keyword(
    date: str,
    point_code: str,
    items: list[dict[str, Any]],
    processed_root: Path | None = None,
) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    rows_by_keyword: dict[str, list[dict[str, Any]]] = {}
    warnings: list[str] = []
    for item in items:
        keyword = str(item["keyword"])
        matches = _priced_matches(date, point_code, keyword, processed_root)
        rows_by_keyword[keyword] = matches
        if not matches:
            aliases = expand_keyword(keyword)
            warnings.append(
                f"No price records found for keyword: {keyword}. Tried aliases: {', '.join(aliases)}"
            )
    return rows_by_keyword, warnings


def _best_plan_for_store_set(
    plan_type: str,
    store_oids: set[Any],
    requested_items: list[dict[str, Any]],
    rows_by_keyword: dict[str, list[dict[str, Any]]],
) -> dict[str, Any] | None:
    selected_items: list[dict[str, Any]] = []
    for item in requested_items:
        keyword = str(item["keyword"])
        requested_quantity = int(item.get("quantity", 1))
        candidates = [
            row
            for row in rows_by_keyword.get(keyword, [])
            if row.get("supermarket_oid") in store_oids
        ]
        if not candidates:
            return None
        cheapest = min(
            candidates,
            key=lambda row: (
                float(row["price_mop"]),
                str(row.get("product_name") or ""),
                str(row.get("supermarket_name") or ""),
            ),
        )
        selected_items.append(_build_plan_item(keyword, requested_quantity, cheapest))

    stores = _stores_from_items(selected_items)
    return {
        "plan_type": plan_type,
        "store_count": len(stores),
        "stores": stores,
        "items": selected_items,
        "estimated_total_mop": _plan_total(selected_items),
    }


def optimize_basket_cheapest_single_store(
    date: str,
    point_code: str,
    items: list[dict[str, Any]],
    processed_root: Path | None = None,
) -> dict[str, Any]:
    rows_by_keyword, warnings = _candidate_rows_by_keyword(date, point_code, items, processed_root)
    store_oids = {
        row.get("supermarket_oid")
        for rows in rows_by_keyword.values()
        for row in rows
        if row.get("supermarket_oid") is not None
    }

    candidates = [
        plan
        for store_oid in store_oids
        if (plan := _best_plan_for_store_set("cheapest_single_store", {store_oid}, items, rows_by_keyword))
    ]

    if candidates:
        best = min(candidates, key=lambda plan: float(plan["estimated_total_mop"]))
        best["date"] = date
        best["point_code"] = point_code
        best["warnings"] = warnings
        return best

    warnings.append("No single store can cover all requested keywords.")
    return {
        "date": date,
        "point_code": point_code,
        "plan_type": "cheapest_single_store",
        "store_count": 0,
        "stores": [],
        "items": [],
        "estimated_total_mop": None,
        "warnings": warnings,
    }


def optimize_basket_cheapest_two_stores(
    date: str,
    point_code: str,
    items: list[dict[str, Any]],
    processed_root: Path | None = None,
) -> dict[str, Any]:
    rows_by_keyword, warnings = _candidate_rows_by_keyword(date, point_code, items, processed_root)
    store_oids = sorted(
        {
            row.get("supermarket_oid")
            for rows in rows_by_keyword.values()
            for row in rows
            if row.get("supermarket_oid") is not None
        },
        key=str,
    )

    candidates: list[dict[str, Any]] = []
    for size in (1, 2):
        for store_group in combinations(store_oids, size):
            plan = _best_plan_for_store_set(
                "cheapest_two_stores",
                set(store_group),
                items,
                rows_by_keyword,
            )
            if plan:
                candidates.append(plan)

    if candidates:
        best = min(
            candidates,
            key=lambda plan: (
                float(plan["estimated_total_mop"]),
                int(plan["store_count"]),
            ),
        )
        best["date"] = date
        best["point_code"] = point_code
        best["warnings"] = warnings
        return best

    warnings.append("No one-store or two-store combination can cover all requested keywords.")
    return {
        "date": date,
        "point_code": point_code,
        "plan_type": "cheapest_two_stores",
        "store_count": 0,
        "stores": [],
        "items": [],
        "estimated_total_mop": None,
        "warnings": warnings,
    }


def optimize_basket(
    date: str,
    point_code: str,
    items: list[dict[str, Any]],
    processed_root: Path | None = None,
) -> dict[str, Any]:
    plans = [
        optimize_basket_cheapest_by_item(date, point_code, items, processed_root),
        optimize_basket_cheapest_single_store(date, point_code, items, processed_root),
        optimize_basket_cheapest_two_stores(date, point_code, items, processed_root),
    ]
    warnings: list[str] = []
    for plan in plans:
        plan.pop("date", None)
        plan.pop("point_code", None)
        warnings.extend(plan.pop("warnings", []))

    deduped_warnings = list(dict.fromkeys(warnings))
    return {
        "date": date,
        "point_code": point_code,
        "plans": plans,
        "warnings": deduped_warnings,
    }
