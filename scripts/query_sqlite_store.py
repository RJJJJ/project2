from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.sqlite_store import DEFAULT_DB_PATH
from services.sqlite_query_service import (
    build_sqlite_simple_basket,
    connect_readonly,
    get_latest_date,
    get_product_price_rows,
    list_collection_points,
    search_product_candidates_for_point,
    search_products,
    table_count,
)


def _error(db_path: Path, message: str) -> dict[str, Any]:
    return {"ok": False, "db_path": str(db_path), "errors": [message]}


def run_query(args: argparse.Namespace) -> tuple[dict[str, Any] | list[dict[str, Any]], int]:
    db_path = Path(args.db_path)
    if not db_path.exists():
        return _error(db_path, f"SQLite DB not found: {db_path}"), 1

    with connect_readonly(db_path) as conn:
        latest_date = get_latest_date(conn)
        date = latest_date if args.date == "latest" else args.date
        if args.mode == "health":
            return {
                "ok": True,
                "db_path": str(db_path),
                "latest_date": latest_date,
                "collection_points_count": table_count(conn, "collection_points"),
                "products_count": table_count(conn, "products"),
                "price_records_count": table_count(conn, "price_records"),
                "supermarkets_count": table_count(conn, "supermarkets"),
            }, 0
        if args.mode == "points":
            return list_collection_points(conn), 0
        if args.mode == "products":
            if not args.keyword:
                return {"ok": False, "errors": ["--keyword is required for products mode"]}, 1
            return {"date": date, "keyword": args.keyword[0], "products": search_products(conn, args.keyword[0], args.limit)}, 0
        if args.mode == "candidates":
            if not args.keyword:
                return {"ok": False, "errors": ["--keyword is required for candidates mode"]}, 1
            return {
                "date": date,
                "point_code": args.point_code,
                "keyword": args.keyword[0],
                "candidates": search_product_candidates_for_point(conn, date, args.point_code, args.keyword[0], args.limit),
            }, 0
        if args.mode == "prices":
            if not args.keyword:
                return {"ok": False, "errors": ["--keyword is required for prices mode"]}, 1
            candidates = search_product_candidates_for_point(conn, date, args.point_code, args.keyword[0], 1)
            rows = get_product_price_rows(conn, date, args.point_code, candidates[0]["product_oid"]) if candidates else []
            return {"date": date, "point_code": args.point_code, "keyword": args.keyword[0], "candidate": candidates[0] if candidates else None, "prices": rows}, 0
        if args.mode == "basket":
            if not args.keyword:
                return {"ok": False, "errors": ["At least one --keyword is required for basket mode"]}, 1
            items = [{"keyword": keyword, "quantity": 1} for keyword in args.keyword]
            return build_sqlite_simple_basket(conn, date, args.point_code, items), 0
    return {"ok": False, "errors": [f"Unsupported mode: {args.mode}"]}, 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Query the local Project2 SQLite store.")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--date", default="latest")
    parser.add_argument("--point-code", default="p001")
    parser.add_argument("--keyword", action="append")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--mode", choices=("health", "points", "products", "candidates", "prices", "basket"), required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    payload, exit_code = run_query(args)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
