from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.utils import get_processed_root, latest_processed_date, resolve_date
from scripts.ask_processed_basket import build_result

QUERIES = [
    "一包米",
    "兩包麵 一包薯條 四包薯片 油 糖 M&M",
    "米 洗頭水 紙巾",
    "油 糖",
    "薯片 薯條",
    "M&M",
]


def run_smoke(point_code: str = "p001", date: str = "latest") -> dict[str, Any]:
    processed_root = get_processed_root()
    selected_date = resolve_date(date, processed_root) if date != "latest" else latest_processed_date(processed_root)
    errors: list[str] = []
    results: list[dict[str, Any]] = []
    if not selected_date:
        return {"ok": False, "queries": [], "errors": ["No processed data date found"]}
    for query in QUERIES:
        try:
            result = build_result(selected_date, point_code, query, processed_root)
            plans = result.get("plans") or []
            first_plan = plans[0] if plans else {}
            results.append(
                {
                    "query": query,
                    "ok": True,
                    "parsed_items_count": len(result.get("parsed_items") or []),
                    "plans_count": len(plans),
                    "is_partial": bool(first_plan.get("is_partial")),
                    "warnings": result.get("warnings") or [],
                }
            )
        except Exception as exc:  # pragma: no cover - smoke diagnostics
            errors.append(f"{query}: {exc}")
            results.append({"query": query, "ok": False, "parsed_items_count": 0, "plans_count": 0, "is_partial": False, "warnings": [], "error": str(exc)})
    return {"ok": not errors and all(item["ok"] for item in results), "queries": results, "errors": errors}


def main() -> int:
    summary = run_smoke()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
