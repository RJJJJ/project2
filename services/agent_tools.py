from __future__ import annotations

from pathlib import Path
from typing import Any

from app.utils import get_processed_root, resolve_date
from services.data_provider_config import get_sqlite_db_path
from services.grounded_answer_formatter import format_grounded_basket_answer
from services.product_candidate_search import search_product_candidates
from services.processed_basket_optimizer import optimize_basket
from services.sqlite_query_service import (
    build_sqlite_simple_basket,
    connect_readonly,
    get_latest_date,
    search_product_candidates_for_point,
)


def _sqlite_conn_and_date(db_path: str | Path | None, date: str):
    path = Path(db_path) if db_path else get_sqlite_db_path()
    if not path.exists():
        raise FileNotFoundError(f"SQLite DB not found: {path}")
    conn = connect_readonly(path)
    selected_date = get_latest_date(conn) if date == "latest" else date
    if not selected_date:
        conn.close()
        raise ValueError("SQLite DB has no latest date")
    return conn, selected_date


def tool_search_product_candidates(args: dict[str, Any]) -> dict[str, Any]:
    provider = str(args.get("provider") or "sqlite").casefold()
    date = str(args.get("date") or "latest")
    point_code = str(args.get("point_code") or "p001")
    keyword = str(args.get("keyword") or "")
    limit = int(args.get("limit") or 10)
    if provider == "sqlite":
        conn, selected_date = _sqlite_conn_and_date(args.get("db_path"), date)
        with conn:
            candidates = search_product_candidates_for_point(conn, selected_date, point_code, keyword, limit)
        return {"ok": True, "provider": "sqlite", "date": selected_date, "point_code": point_code, "keyword": keyword, "candidates": candidates}
    processed_root = Path(args.get("processed_root") or get_processed_root())
    selected_date = resolve_date(date, processed_root)
    return {
        "ok": True,
        "provider": "jsonl",
        "date": selected_date,
        "point_code": point_code,
        "keyword": keyword,
        "candidates": search_product_candidates(selected_date, point_code, keyword, limit=limit, processed_root=processed_root),
    }


def tool_build_basket(args: dict[str, Any]) -> dict[str, Any]:
    provider = str(args.get("provider") or "sqlite").casefold()
    date = str(args.get("date") or "latest")
    point_code = str(args.get("point_code") or "p001")
    items = args.get("items") or []
    if provider == "sqlite":
        conn, selected_date = _sqlite_conn_and_date(args.get("db_path"), date)
        with conn:
            result = build_sqlite_simple_basket(conn, selected_date, point_code, items)
        result["provider"] = "sqlite"
        return {"ok": True, "basket_result": result}
    processed_root = Path(args.get("processed_root") or get_processed_root())
    selected_date = resolve_date(date, processed_root)
    result = optimize_basket(selected_date, point_code, items, processed_root)
    result["date"] = selected_date
    result["point_code"] = point_code
    result["parsed_items"] = items
    result["provider"] = "jsonl"
    return {"ok": True, "basket_result": result}


def tool_format_answer(args: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "answer": format_grounded_basket_answer(args.get("basket_result") or {}, style=str(args.get("style") or "simple"))}
