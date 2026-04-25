from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from services.processed_data_loader import build_supermarket_lookup, load_price_records


def _priced_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("price_mop") is not None and row.get("product_oid") is not None]


def _with_supermarket_name(row: dict[str, Any], lookup: dict[int, dict[str, Any]]) -> dict[str, Any]:
    output = dict(row)
    supermarket_oid = output.get("supermarket_oid")
    supermarket = lookup.get(int(supermarket_oid)) if supermarket_oid is not None else None
    output["supermarket_name"] = supermarket.get("supermarket_name") if supermarket else output.get("supermarket_name")
    return output


def analyze_point_signals(
    date: str,
    point_code: str,
    processed_root: Path | None = None,
) -> dict[str, Any]:
    rows = load_price_records(date, point_code, processed_root)
    lookup = build_supermarket_lookup(date, point_code, processed_root)
    priced_rows = [_with_supermarket_name(row, lookup) for row in _priced_rows(rows)]

    rows_by_product: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for row in priced_rows:
        rows_by_product[row.get("product_oid")].append(row)

    cheapest_products = []
    largest_gaps = []
    for product_oid, product_rows in rows_by_product.items():
        sorted_rows = sorted(product_rows, key=lambda row: float(row["price_mop"]))
        cheapest = sorted_rows[0]
        most_expensive = sorted_rows[-1]
        min_price = float(cheapest["price_mop"])
        max_price = float(most_expensive["price_mop"])
        cheapest_products.append(
            {
                "product_oid": product_oid,
                "product_name": cheapest.get("product_name"),
                "quantity": cheapest.get("quantity"),
                "category_id": cheapest.get("category_id"),
                "category_name": cheapest.get("category_name"),
                "min_price_mop": min_price,
                "supermarket_oid": cheapest.get("supermarket_oid"),
                "supermarket_name": cheapest.get("supermarket_name"),
            }
        )

        if len({row.get("supermarket_oid") for row in product_rows}) < 2 or min_price <= 0:
            continue
        gap_mop = max_price - min_price
        largest_gaps.append(
            {
                "product_oid": product_oid,
                "product_name": cheapest.get("product_name"),
                "quantity": cheapest.get("quantity"),
                "category_id": cheapest.get("category_id"),
                "category_name": cheapest.get("category_name"),
                "min_price_mop": min_price,
                "max_price_mop": max_price,
                "gap_mop": gap_mop,
                "gap_percent": gap_mop / min_price * 100,
                "min_supermarket_oid": cheapest.get("supermarket_oid"),
                "min_supermarket_name": cheapest.get("supermarket_name"),
                "max_supermarket_oid": most_expensive.get("supermarket_oid"),
                "max_supermarket_name": most_expensive.get("supermarket_name"),
            }
        )

    coverage_counter: Counter[Any] = Counter(
        row.get("supermarket_oid") for row in rows if row.get("supermarket_oid") is not None
    )
    store_count_coverage = []
    for supermarket_oid, count in coverage_counter.most_common(20):
        supermarket = lookup.get(int(supermarket_oid))
        store_count_coverage.append(
            {
                "supermarket_oid": supermarket_oid,
                "supermarket_name": supermarket.get("supermarket_name") if supermarket else None,
                "price_records": count,
            }
        )

    return {
        "date": date,
        "point_code": point_code,
        "cheapest_products_by_keyword": sorted(
            cheapest_products,
            key=lambda item: (item["min_price_mop"], str(item.get("product_name") or "")),
        )[:20],
        "largest_price_gap": sorted(
            largest_gaps,
            key=lambda item: (item["gap_percent"], item["gap_mop"]),
            reverse=True,
        )[:20],
        "store_count_coverage": store_count_coverage,
    }
