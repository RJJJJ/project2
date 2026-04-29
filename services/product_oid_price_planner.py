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



def _best_options_by_item(rows: list[dict[str, Any]], quantity: int) -> list[dict[str, Any]]:
    best_by_store: dict[str, dict[str, Any]] = {}
    for row in rows:
        store_oid = row.get("supermarket_oid")
        if store_oid is None:
            continue
        store_key = str(store_oid)
        unit_price = float(row.get("price_mop") or 0)
        subtotal = round(quantity * unit_price, 2)
        option = {
            "supermarket_oid": store_key,
            "supermarket_name": row.get("supermarket_name"),
            "selected_product_oid": row.get("product_oid"),
            "selected_product_name": row.get("product_name"),
            "package_quantity": row.get("package_quantity"),
            "unit_price_mop": unit_price,
            "subtotal_mop": subtotal,
        }
        current = best_by_store.get(store_key)
        if current is None or (
            subtotal,
            str(option.get("selected_product_name") or ""),
            str(option.get("selected_product_oid") or ""),
        ) < (
            float(current.get("subtotal_mop") or 0),
            str(current.get("selected_product_name") or ""),
            str(current.get("selected_product_oid") or ""),
        ):
            best_by_store[store_key] = option
    return sorted(
        best_by_store.values(),
        key=lambda option: (
            float(option.get("subtotal_mop") or 0),
            str(option.get("supermarket_name") or ""),
            str(option.get("supermarket_oid") or ""),
            str(option.get("selected_product_name") or ""),
        ),
    )


def _store_pair_keys(store_oids: list[str]) -> list[tuple[str, ...]]:
    unique = sorted(dict.fromkeys(str(oid) for oid in store_oids if oid is not None))
    pairs: list[tuple[str, ...]] = [(oid,) for oid in unique]
    for idx, left in enumerate(unique):
        for right in unique[idx + 1 :]:
            pairs.append((left, right))
    return pairs


def plan_cheapest_by_product_candidates_two_stores(
    db_path: str | Path,
    point_code: str | None,
    priceable_items: list[dict[str, Any]],
    max_candidates_per_item: int = 5,
) -> dict[str, Any]:
    strategy = "cheapest_two_stores"
    warnings: list[str] = []
    if not point_code:
        return {
            "status": "not_priceable",
            "strategy": strategy,
            "store_plans": [],
            "best_plan": None,
            "item_availability": [],
            "warnings": ["point_code is required for two-store price planning."],
            "diagnostics": {"priceable_item_count": len(priceable_items or []), "plan_count": 0, "two_store_plan_count": 0},
        }
    if not priceable_items:
        return {
            "status": "not_priceable",
            "strategy": strategy,
            "store_plans": [],
            "best_plan": None,
            "item_availability": [],
            "warnings": ["No priceable resolved items."],
            "diagnostics": {"priceable_item_count": 0, "plan_count": 0, "two_store_plan_count": 0},
        }
    if not Path(db_path).exists():
        return {
            "status": "not_priceable",
            "strategy": strategy,
            "store_plans": [],
            "best_plan": None,
            "item_availability": [],
            "warnings": [f"SQLite database not found: {db_path}"],
            "diagnostics": {"priceable_item_count": len(priceable_items), "plan_count": 0, "two_store_plan_count": 0},
        }

    with _connect(db_path) as conn:
        date = get_latest_date(conn)
        if not date:
            return {
                "status": "not_priceable",
                "strategy": strategy,
                "store_plans": [],
                "best_plan": None,
                "item_availability": [],
                "warnings": ["No price_records date found."],
                "diagnostics": {"priceable_item_count": len(priceable_items), "plan_count": 0, "two_store_plan_count": 0},
            }
        availability: list[dict[str, Any]] = []
        all_store_oids: set[str] = set()
        for item in priceable_items:
            trimmed_item = dict(item)
            trimmed_item["candidate_products"] = list(item.get("candidate_products") or [])[: max(1, int(max_candidates_per_item or 1))]
            quantity = _quantity(trimmed_item)
            rows = _fetch_rows(conn, date, str(point_code), _candidate_oids(trimmed_item))
            options = _best_options_by_item(rows, quantity)
            all_store_oids.update(str(option["supermarket_oid"]) for option in options)
            availability.append(
                {
                    "raw_item_name": trimmed_item.get("raw_item_name"),
                    "intent_id": trimmed_item.get("intent_id"),
                    "quantity": quantity,
                    "available_store_options": options,
                }
            )

    store_plans: list[dict[str, Any]] = []
    for pair in _store_pair_keys(list(all_store_oids)):
        selected_items: list[dict[str, Any]] = []
        missing_items: list[dict[str, Any]] = []
        used_stores: dict[str, str | None] = {}
        total = 0.0
        for item_availability in availability:
            options = [option for option in item_availability["available_store_options"] if str(option.get("supermarket_oid")) in pair]
            if not options:
                missing_items.append({"raw_item_name": item_availability.get("raw_item_name"), "intent_id": item_availability.get("intent_id")})
                continue
            best = sorted(
                options,
                key=lambda option: (
                    float(option.get("subtotal_mop") or 0),
                    str(option.get("supermarket_name") or ""),
                    str(option.get("supermarket_oid") or ""),
                    str(option.get("selected_product_name") or ""),
                ),
            )[0]
            store_oid = str(best.get("supermarket_oid"))
            used_stores[store_oid] = best.get("supermarket_name")
            subtotal = float(best.get("subtotal_mop") or 0)
            total += subtotal
            selected_items.append(
                {
                    "raw_item_name": item_availability.get("raw_item_name"),
                    "intent_id": item_availability.get("intent_id"),
                    "quantity": item_availability.get("quantity", 1),
                    "selected_store_oid": store_oid,
                    "selected_store_name": best.get("supermarket_name"),
                    "selected_product_oid": best.get("selected_product_oid"),
                    "selected_product_name": best.get("selected_product_name"),
                    "package_quantity": best.get("package_quantity"),
                    "unit_price_mop": best.get("unit_price_mop"),
                    "subtotal_mop": round(subtotal, 2),
                }
            )
        if missing_items:
            continue
        sorted_used = sorted(used_stores.items(), key=lambda kv: (str(kv[1] or ""), str(kv[0])))
        store_plans.append(
            {
                "strategy": strategy,
                "supermarket_oids": [oid for oid, _name in sorted_used],
                "supermarket_names": [name for _oid, name in sorted_used],
                "point_code": point_code,
                "store_count": len(sorted_used),
                "estimated_total_mop": round(total, 2),
                "items": selected_items,
                "missing_items": [],
            }
        )

    store_plans.sort(
        key=lambda plan: (
            float(plan.get("estimated_total_mop") or 0),
            int(plan.get("store_count") or 0),
            ",".join(str(name) for name in plan.get("supermarket_names") or []),
            ",".join(str(oid) for oid in plan.get("supermarket_oids") or []),
        )
    )
    best_plan = store_plans[0] if store_plans else None
    if not best_plan:
        missing_count = sum(1 for item in availability if not item.get("available_store_options"))
        if missing_count:
            warnings.append(f"{missing_count} priceable item(s) have no available store price records.")
        warnings.append("No one- or two-store combination can cover all priceable items.")
    return {
        "status": "ok" if best_plan else "not_priceable",
        "strategy": strategy,
        "store_plans": store_plans,
        "best_plan": best_plan,
        "item_availability": availability,
        "warnings": warnings,
        "diagnostics": {
            "date": date,
            "point_code": point_code,
            "priceable_item_count": len(priceable_items),
            "available_store_count": len(all_store_oids),
            "plan_count": len(store_plans),
            "two_store_plan_count": len(store_plans),
        },
    }
