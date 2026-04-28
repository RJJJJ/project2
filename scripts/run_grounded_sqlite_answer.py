from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from services.collection_point_resolver import PointResolutionError, resolve_point_code
from services.gemini_intent_parser import parse_intent
from services.grounded_answer_formatter import format_grounded_basket_answer
from services.sqlite_query_service import build_sqlite_simple_basket, connect_readonly, get_latest_date


def _resolve_point(intent: dict, default_point_code: str) -> str:
    if intent.get("point_code"):
        return str(intent["point_code"])
    if intent.get("location_text"):
        try:
            return str(resolve_point_code(point_name=str(intent["location_text"]))["point_code"])
        except PointResolutionError:
            pass
    return default_point_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run grounded SQLite basket answer prototype.")
    parser.add_argument("--text", required=True)
    parser.add_argument("--point-code", default="p001")
    parser.add_argument("--db-path", type=Path, default=PROJECT_ROOT / "data" / "app_state" / "project2_dev.sqlite3")
    parser.add_argument("--date", default="latest")
    parser.add_argument("--use-gemini", action="store_true")
    parser.add_argument("--polish", action="store_true")
    args = parser.parse_args(argv)
    if not args.db_path.exists():
        print(json.dumps({"ok": False, "errors": [f"SQLite DB not found: {args.db_path}"]}, ensure_ascii=False, indent=2))
        return 1
    intent = parse_intent(args.text, use_gemini=args.use_gemini)
    point_code = _resolve_point(intent, args.point_code)
    with connect_readonly(args.db_path) as conn:
        date = get_latest_date(conn) if args.date == "latest" else args.date
        basket = build_sqlite_simple_basket(conn, str(date), point_code, intent.get("items", []))
    answer = format_grounded_basket_answer(basket)
    print(json.dumps({"intent": intent, "basket_result": basket, "answer": answer}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
