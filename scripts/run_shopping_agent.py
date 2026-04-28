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

from services.shopping_agent_orchestrator import run_shopping_agent
from services.sqlite_store import DEFAULT_DB_PATH


def main() -> int:
    parser = argparse.ArgumentParser(description="Run rule-first shopping agent intent resolution.")
    parser.add_argument("--query", required=True)
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--point-code")
    parser.add_argument("--use-llm", action="store_true")
    parser.add_argument("--include-price-plan", action="store_true")
    parser.add_argument("--price-strategy", default="cheapest_single_store")
    parser.add_argument("--max-candidates-per-item", type=int, default=5)
    parser.add_argument("--debug-json", action="store_true")
    args = parser.parse_args()

    result = run_shopping_agent(
        args.query,
        Path(args.db_path),
        point_code=args.point_code,
        use_llm=args.use_llm,
        debug=args.debug_json,
        include_price_plan=args.include_price_plan,
        price_strategy=args.price_strategy,
        max_candidates_per_item=args.max_candidates_per_item,
    )
    if args.debug_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result.get("user_message_zh") or "")
    return 0 if result.get("status") != "error" else 1


if __name__ == "__main__":
    raise SystemExit(main())
