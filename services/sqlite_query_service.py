from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from services.sqlite_store import DEFAULT_DB_PATH
from services.product_matching_rules import (
    candidate_text_match_score,
    expand_keyword,
    is_forbidden_match,
)


RECOMMENDATION_REASON = "\u6839\u64da\u5546\u54c1\u540d\u7a31\u5339\u914d\u3001\u5e38\u898b\u898f\u683c\u3001\u8986\u84cb\u8d85\u5e02\u6578\u91cf\u53ca\u6700\u4f4e\u50f9\u6392\u5e8f\u3002"


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def connect_readonly(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    try:
        uri = f"file:{path.resolve().as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.OperationalError:
        conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def get_latest_date(conn: sqlite3.Connection) -> str | None:
    row = conn.execute("SELECT MAX(date) AS latest_date FROM price_records").fetchone()
    return row["latest_date"] if row and row["latest_date"] is not None else None


def list_collection_points(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT point_code, name, district, lat, lng, dst
        FROM collection_points
        ORDER BY point_code ASC
        """
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def _build_like_clause(terms: list[str]) -> tuple[str, list[str]]:
    clauses: list[str] = []
    params: list[str] = []
    for term in terms:
        like = f"%{term}%"
        clauses.append("(product_name LIKE ? OR category_name LIKE ?)")
        params.extend([like, like])
    return " OR ".join(clauses), params


def _product_sort_key(keyword: str, item: dict[str, Any]) -> tuple[float, int, str, str]:
    score = candidate_text_match_score(keyword, item.get("product_name"), item.get("package_quantity"), item.get("category_name"))
    return (-score, int(item.get("category_id") or 0), str(item.get("product_name") or ""), str(item.get("product_oid") or ""))


def search_products(conn: sqlite3.Connection, keyword: str, limit: int = 20) -> list[dict[str, Any]]:
    normalized = keyword.strip()
    if not normalized:
        return []
    terms = expand_keyword(normalized)
    where_clause, params = _build_like_clause(terms)
    rows = conn.execute(
        f"""
        SELECT product_oid, product_name, package_quantity, category_id, category_name
        FROM products
        WHERE {where_clause}
        """,
        params,
    ).fetchall()
    products = [_row_to_dict(row) for row in rows]
    products.sort(key=lambda item: _product_sort_key(normalized, item))
    return products[: max(0, int(limit))]

def get_product_price_rows(conn: sqlite3.Connection, date: str, point_code: str, product_oid: str | int) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
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
        WHERE pr.date = ? AND pr.point_code = ? AND pr.product_oid = ?
        ORDER BY pr.price_mop ASC, s.supermarket_name ASC, pr.supermarket_oid ASC
        """,
        (date, point_code, str(product_oid)),
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def search_product_candidates_for_point(
    conn: sqlite3.Connection,
    date: str,
    point_code: str,
    keyword: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    normalized = keyword.strip()
    if not normalized:
        return []
    terms = expand_keyword(normalized)
    like_clauses: list[str] = []
    params: list[Any] = [date, point_code]
    for term in terms:
        like = f"%{term}%"
        like_clauses.append("(p.product_name LIKE ? OR p.category_name LIKE ?)")
        params.extend([like, like])
    where_like = " OR ".join(like_clauses)
    rows = conn.execute(
        f"""
        SELECT
            p.product_oid,
            p.product_name,
            p.package_quantity,
            p.category_id,
            p.category_name,
            MIN(pr.price_mop) AS min_price_mop,
            MAX(pr.price_mop) AS max_price_mop,
            COUNT(DISTINCT pr.supermarket_oid) AS store_count
        FROM products p
        JOIN price_records pr ON pr.product_oid = p.product_oid
        WHERE pr.date = ? AND pr.point_code = ? AND ({where_like})
        GROUP BY p.product_oid, p.product_name, p.package_quantity, p.category_id, p.category_name
        """,
        params,
    ).fetchall()

    scored: list[dict[str, Any]] = []
    for row in rows:
        item = _row_to_dict(row)
        min_price = float(item["min_price_mop"] or 0)
        store_count = int(item["store_count"] or 0)
        forbidden = is_forbidden_match(normalized, item.get("product_name"), item.get("category_name"))
        match_score = candidate_text_match_score(normalized, item.get("product_name"), item.get("package_quantity"), item.get("category_name"))
        if forbidden:
            match_score -= 200
        coverage_score = float(store_count)
        price_score = -min_price * 0.01
        final_score = match_score * 100 + coverage_score * 5 + price_score
        item.update(
            {
                "match_score": round(match_score, 2),
                "ranking_factors": {
                    "match_score": round(match_score, 2),
                    "coverage_score": round(coverage_score, 2),
                    "price_score": round(price_score, 2),
                    "final_score": round(final_score, 2),
                },
                "final_score": round(final_score, 2),
                "forbidden_match": forbidden,
                "is_recommended": False,
                "recommendation_reason": "",
            }
        )
        scored.append(item)

    filtered = [item for item in scored if not item.get("forbidden_match") and float(item["match_score"]) >= -5.0]
    if filtered:
        scored = filtered

    scored.sort(
        key=lambda item: (
            -float(item["final_score"]),
            -int(item["store_count"] or 0),
            float(item["min_price_mop"] or 0),
            str(item.get("product_name") or ""),
            str(item.get("product_oid") or ""),
        )
    )
    limited = scored[: max(0, int(limit))]
    for index, item in enumerate(limited):
        item["is_recommended"] = index == 0
        item["recommendation_reason"] = RECOMMENDATION_REASON if index == 0 else ""
    return limited

def get_cheapest_offer_for_keyword(conn: sqlite3.Connection, date: str, point_code: str, keyword: str) -> dict[str, Any] | None:
    candidates = search_product_candidates_for_point(conn, date, point_code, keyword, limit=1)
    if not candidates:
        return None
    candidate = candidates[0]
    rows = get_product_price_rows(conn, date, point_code, candidate["product_oid"])
    if not rows:
        return None
    cheapest = rows[0]
    return {
        "keyword": keyword,
        "product_oid": cheapest["product_oid"],
        "product_name": cheapest["product_name"],
        "package_quantity": cheapest["package_quantity"],
        "category_name": cheapest["category_name"],
        "supermarket_oid": cheapest["supermarket_oid"],
        "supermarket_name": cheapest["supermarket_name"],
        "unit_price_mop": cheapest["price_mop"],
        "source": "sqlite",
    }


def build_sqlite_simple_basket(conn: sqlite3.Connection, date: str, point_code: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    result_items: list[dict[str, Any]] = []
    warnings: list[str] = []
    total = 0.0
    for item in items:
        keyword = str(item.get("keyword") or "").strip()
        quantity = int(item.get("quantity") or 1)
        offer = get_cheapest_offer_for_keyword(conn, date, point_code, keyword) if keyword else None
        if not offer:
            warnings.append(f"No SQLite offer found for keyword: {keyword}")
            result_items.append({"keyword": keyword, "quantity": quantity, "matched": False})
            continue
        unit_price = float(offer["unit_price_mop"])
        subtotal = round(unit_price * quantity, 2)
        total += subtotal
        result_items.append(
            {
                "keyword": keyword,
                "quantity": quantity,
                "matched": True,
                "product_oid": offer["product_oid"],
                "product_name": offer["product_name"],
                "package_quantity": offer["package_quantity"],
                "supermarket_oid": offer["supermarket_oid"],
                "supermarket_name": offer["supermarket_name"],
                "unit_price_mop": unit_price,
                "subtotal_mop": subtotal,
            }
        )
    return {
        "date": date,
        "point_code": point_code,
        "items": result_items,
        "estimated_total_mop": round(total, 2),
        "warnings": warnings,
    }


def table_count(conn: sqlite3.Connection, table: str) -> int:
    if table not in {"collection_points", "products", "price_records", "supermarkets"}:
        raise ValueError(f"Unsupported table: {table}")
    return int(conn.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()["count"])

