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

from services.agent_tools import tool_build_basket, tool_format_answer
from services.gemini_intent_parser import parse_intent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run deterministic agent tool interface demo.")
    parser.add_argument("--text", required=True)
    parser.add_argument("--provider", choices=("sqlite", "jsonl"), default="sqlite")
    parser.add_argument("--point-code", default="p001")
    parser.add_argument("--date", default="latest")
    parser.add_argument("--db-path", type=Path, default=PROJECT_ROOT / "data" / "app_state" / "project2_dev.sqlite3")
    args = parser.parse_args(argv)
    intent = parse_intent(args.text, use_gemini=False)
    tool_calls = []
    warnings = []
    try:
        basket_call = tool_build_basket({"provider": args.provider, "date": args.date, "point_code": args.point_code, "items": intent.get("items", []), "db_path": args.db_path})
        tool_calls.append({"tool": "tool_build_basket", "ok": bool(basket_call.get("ok"))})
        answer_call = tool_format_answer({"basket_result": basket_call.get("basket_result"), "style": "simple"})
        tool_calls.append({"tool": "tool_format_answer", "ok": bool(answer_call.get("ok"))})
        payload = {"ok": True, "intent": intent, "tool_calls": tool_calls, "answer": answer_call["answer"], "warnings": warnings}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "intent": intent, "tool_calls": tool_calls, "answer": None, "warnings": warnings, "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
