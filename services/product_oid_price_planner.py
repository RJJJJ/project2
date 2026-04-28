from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from services.sqlite_query_service import get_latest_date


def _connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(Path(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _candidate_oids(item: dict[str, Any]) -> list[str]:
    oids: list[str] = []
    for candidate in item.get("candidate_products") or []:
        oid = candidate.get("product_oid")
        if oid is not None:
            oids.append(str(oid))
    return list(dict.fromkeys(oids))


def _quantity(item: dict[str, Any]) -> int:
    try:
        return max(1, int(item.get("quantity") or 1))
    except (TypeError, ValueError):
        return 1


def _fetch_rows(
    conn: sqlite3.Connection,
    date: str,
    point_code: str,
    product_oids: list[str],
) -> list[dict[str, Any]]:
    if not product_oids:
        return []
    placeholders = ",".join("?" for _ in product_oids)
    rows = conn.execute(
        f"""
        SELECT
            pr.date,
            pr.point_code,
            pr.product_oid,
            p.product_name,
            p.package_quantity,
            pr.category_id,
            p.category_name,
            pr.supermarket_oid,
            s.supermarket_name,
            pr.price_mop
        FROM price_records pr
        JOIN products p ON p.product_oid = pr.product_oid
        LEFT JOIN supermarkets s ON s.supermarket_oid = pr.supermarket_oid
        WHERE pr.date = ?
          AND pr.point_code = ?
          AND pr.product_oid IN ({placeholders})
          AND pr.price_mop IS NOT NULL
        """,
        [date, point_code, *product_oids],
    ).fetchall()
    return [dict(row) for row in rows]


def _best_row_for_store(rows: list[dict[str, Any]], store_oid: str) -> dict[str, Any] | None:
    matching = [row for row in rows if str(row.get("supermarket_oid")) == store_oid]
    if not matching:
        return None
    return min(
        matching,
        key=lambda row: (
            float(row.get("price_mop") or 0),
            str(row.get("product_name") or ""),
            str(row.get("product_oid") or ""),
        ),
    )


def plan_cheapest_by_product_candidates(
    db_path: str | Path,
    point_code: str | None,
    priceable_items: list[dict[str, Any]],
    strategy: str = "cheapest_single_store",
) -> dict[str, Any]:
    warnings: list[str] = []
    if strategy != "cheapest_single_store":
        warnings.append(f"Unsupported strategy {strategy}; falling back to cheapest_single_store.")
        strategy = "cheapest_single_store"
    if not point_code:
        return {
            "status": "not_priceable",
            "strategy": strategy,
            "store_plans": [],
            "best_plan": None,
            "warnings": ["point_code is required for price planning."],
            "diagnostics": {"priceable_item_count": len(priceable_items), "plan_count": 0},
        }
    if not priceable_items:
        return {
            "status": "not_priceable",
            "strategy": strategy,
            "store_plans": [],
            "best_plan": None,
            "warnings": ["No priceable resolved items."],
            "diagnostics": {"priceable_item_count": 0, "plan_count": 0},
        }
    if not Path(db_path).exists():
        return {
            "status": "not_priceable",
            "strategy": strategy,
            "store_plans": [],
            "best_plan": None,
            "warnings": [f"SQLite database not found: {db_path}"],
            "diagnostics": {"priceable_item_count": len(priceable_items), "plan_count": 0},
        }

    with _connect(db_path) as conn:
        date = get_latest_date(conn)
        if not date:
            return {
                "status": "not_priceable",
                "strategy": strategy,
                "store_plans": [],
                "best_plan": None,
                "warnings": ["No price_records date found."],
                "diagnostics": {"priceable_item_count": len(priceable_items), "plan_count": 0},
            }
        rows_by_item: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
        all_store_oids: set[str] = set()
        for item in priceable_items:
            rows = _fetch_rows(conn, date, str(point_code), _candidate_oids(item))
            rows_by_item.append((item, rows))
            all_store_oids.update(str(row.get("supermarket_oid")) for row in rows if row.get("supermarket_oid") is not None)

    store_plans: list[dict[str, Any]] = []
    for store_oid in sorted(all_store_oids):
        plan_items: list[dict[str, Any]] = []
        missing_items: list[dict[str, Any]] = []
        store_name = None
        total = 0.0
        for item, rows in rows_by_item:
            row = _best_row_for_store(rows, store_oid)
            if row is None:
                missing_items.append({"raw_item_name": item.get("raw_item_name"), "intent_id": item.get("intent_id")})
                continue
            quantity = _quantity(item)
            unit_price = float(row.get("price_mop") or 0)
            subtotal = round(quantity * unit_price, 2)
            total += subtotal
            store_name = store_name or row.get("supermarket_name")
            plan_items.append(
                {
                    "raw_item_name": item.get("raw_item_name"),
                    "intent_id": item.get("intent_id"),
                    "quantity": quantity,
                    "selected_product_oid": row.get("product_oid"),
                    "selected_product_name": row.get("product_name"),
                    "package_quantity": row.get("package_quantity"),
                    "unit_price_mop": unit_price,
                    "subtotal_mop": subtotal,
                }
            )
        if missing_items:
            continue
        store_plans.append(
            {
                "supermarket_oid": store_oid,
                "supermarket_name": store_name,
                "point_code": point_code,
                "store_count": 1,
                "estimated_total_mop": round(total, 2),
                "items": plan_items,
                "missing_items": [],
            }
        )

    store_plans.sort(key=lambda plan: (float(plan["estimated_total_mop"]), str(plan.get("supermarket_name") or ""), str(plan.get("supermarket_oid") or "")))
    best_plan = store_plans[0] if store_plans else None
    if not best_plan:
        warnings.append("未能找到同一超市同時覆蓋所有已解析商品的價格。")
    return {
        "status": "ok" if best_plan else "not_priceable",
        "strategy": strategy,
        "store_plans": store_plans,
        "best_plan": best_plan,
        "warnings": warnings,
        "diagnostics": {
            "date": date,
            "point_code": point_code,
            "priceable_item_count": len(priceable_items),
            "plan_count": len(store_plans),
        },
    }
