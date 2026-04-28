from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    try:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    except sqlite3.Error:
        return set()
    return {str(row[1]) for row in rows}


def _select_expr(columns: set[str], candidates: list[str], alias: str, default: str = "NULL") -> str:
    for column in candidates:
        if column in columns:
            return f"{column} AS {alias}"
    return f"{default} AS {alias}"


def load_products_from_sqlite(db_path: str | Path) -> list[dict[str, Any]]:
    path = Path(db_path)
    if not path.exists():
        return []

    try:
        conn = sqlite3.connect(path)
    except sqlite3.Error:
        return []
    conn.row_factory = sqlite3.Row
    try:
        columns = _column_names(conn, "products")
        if not columns:
            return []
        select_sql = ", ".join(
            [
                _select_expr(columns, ["product_oid", "item_oid", "oid", "id"], "product_oid"),
                _select_expr(columns, ["product_name", "name", "name_cn"], "product_name"),
                _select_expr(columns, ["category_id", "category"], "category_id"),
                _select_expr(columns, ["category_name", "category_label"], "category_name", "''"),
                _select_expr(columns, ["package_quantity", "quantity", "package"], "package_quantity", "''"),
            ]
        )
        rows = conn.execute(f"SELECT {select_sql} FROM products").fetchall()
        return [dict(row) for row in rows if row["product_name"]]
    finally:
        conn.close()
