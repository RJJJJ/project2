from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from services.processed_data_loader import (
    build_supermarket_lookup,
    load_price_records,
    load_supermarkets,
)


def _match_keyword(row: dict[str, Any], keyword: str) -> bool:
    normalized = keyword.strip().casefold()
    if not normalized:
        return True
    fields = (
        row.get("product_name"),
        row.get("quantity"),
        row.get("category_name"),
    )
    return any(normalized in str(value).casefold() for value in fields if value is not None)


def _join_supermarket_names(
    rows: list[dict[str, Any]],
    supermarket_lookup: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    joined: list[dict[str, Any]] = []
    for row in rows:
        output = dict(row)
        supermarket_oid = row.get("supermarket_oid")
        supermarket = None
        if supermarket_oid is not None:
            supermarket = supermarket_lookup.get(int(supermarket_oid))
        output["supermarket_name"] = supermarket.get("supermarket_name") if supermarket else None
        joined.append(output)
    return joined


def search_products(
    date: str,
    point_code: str,
    keyword: str,
    processed_root: Path | None = None,
) -> list[dict[str, Any]]:
    seen: set[Any] = set()
    products: list[dict[str, Any]] = []
    for row in load_price_records(date, point_code, processed_root):
        if not _match_keyword(row, keyword):
            continue
        product_oid = row.get("product_oid")
        if product_oid in seen:
            continue
        seen.add(product_oid)
        products.append(
            {
                "product_oid": product_oid,
                "product_name": row.get("product_name"),
                "quantity": row.get("quantity"),
                "category_id": row.get("category_id"),
                "category_name": row.get("category_name"),
            }
        )
    return products


def get_prices_for_keyword(
    date: str,
    point_code: str,
    keyword: str,
    processed_root: Path | None = None,
) -> list[dict[str, Any]]:
    rows = [
        row
        for row in load_price_records(date, point_code, processed_root)
        if _match_keyword(row, keyword)
    ]
    lookup = build_supermarket_lookup(date, point_code, processed_root)
    return _join_supermarket_names(rows, lookup)


def get_cheapest_prices_for_keyword(
    date: str,
    point_code: str,
    keyword: str,
    limit: int = 10,
    processed_root: Path | None = None,
) -> list[dict[str, Any]]:
    rows = [
        row
        for row in get_prices_for_keyword(date, point_code, keyword, processed_root)
        if row.get("price_mop") is not None
    ]
    rows.sort(key=lambda row: (float(row["price_mop"]), str(row.get("product_name") or "")))
    return rows[:limit]


def get_category_summary(
    date: str,
    point_code: str,
    processed_root: Path | None = None,
) -> list[dict[str, Any]]:
    counter: Counter[tuple[Any, Any]] = Counter()
    for row in load_price_records(date, point_code, processed_root):
        counter[(row.get("category_id"), row.get("category_name"))] += 1
    return [
        {"category_id": category_id, "category_name": category_name, "price_records": count}
        for (category_id, category_name), count in sorted(
            counter.items(),
            key=lambda item: (item[0][0] is None, item[0][0] or 0, str(item[0][1] or "")),
        )
    ]


def get_point_overview(
    date: str,
    point_code: str,
    processed_root: Path | None = None,
) -> dict[str, Any]:
    supermarkets = load_supermarkets(date, point_code, processed_root)
    price_records = get_prices_for_keyword(date, point_code, "", processed_root)
    product_oids = {row.get("product_oid") for row in price_records if row.get("product_oid") is not None}
    priced_rows = [row for row in price_records if row.get("price_mop") is not None]
    cheapest = sorted(priced_rows, key=lambda row: float(row["price_mop"]))[:10]
    most_expensive = sorted(priced_rows, key=lambda row: float(row["price_mop"]), reverse=True)[:10]

    return {
        "supermarket_count": len(supermarkets),
        "product_count": len(product_oids),
        "price_record_count": len(price_records),
        "category_counts": get_category_summary(date, point_code, processed_root),
        "top_10_cheapest_records": cheapest,
        "top_10_most_expensive_records": most_expensive,
    }
