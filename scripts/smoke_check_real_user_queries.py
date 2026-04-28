from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


QUERIES = [
    "糖",
    "朱古力",
    "麵",
    "糖 朱古力 麵",
    "兩包麵 一包薯條 四包薯片 油 糖 M&M",
    "米 洗頭水 紙巾",
    "???",
]

REQUIRED_PARSED = {
    "糖",
    "朱古力",
    "麵",
    "糖 朱古力 麵",
    "兩包麵 一包薯條 四包薯片 油 糖 M&M",
    "米 洗頭水 紙巾",
}


def _post_with_test_client(path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    from fastapi.testclient import TestClient

    from app.main import app

    response = TestClient(app).post(path, json=payload)
    return response.status_code, response.json()


def _post_with_requests(base_url: str, path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    import requests

    response = requests.post(f"{base_url.rstrip('/')}{path}", json=payload, timeout=30)
    return response.status_code, response.json()


def _is_misleading_empty_plan(data: dict[str, Any]) -> bool:
    if data.get("parsed_items"):
        return False
    for plan in data.get("plans") or []:
        if plan.get("plan_type") in {"cheapest_by_item", "cheapest_single_store", "cheapest_two_stores"}:
            return True
    return False


def run_smoke(base_url: str = "", point_code: str = "p001", date: str = "latest") -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    checks: list[dict[str, Any]] = []
    post = _post_with_requests if base_url else None

    for query in QUERIES:
        try:
            payload = {"text": query, "point_code": point_code, "date": date}
            if post:
                status_code, data = post(base_url, "/api/basket/ask", payload)
            else:
                status_code, data = _post_with_test_client("/api/basket/ask", payload)
        except Exception as exc:  # pragma: no cover - smoke diagnostics
            errors.append(f"{query}: {exc}")
            checks.append(
                {
                    "query": query,
                    "ok": False,
                    "status_code": 0,
                    "parsed_items_count": 0,
                    "plans_count": 0,
                    "warnings": [],
                    "error": str(exc),
                }
            )
            continue

        parsed_items = data.get("parsed_items") or []
        plans = data.get("plans") or []
        query_errors: list[str] = []
        if status_code >= 500:
            query_errors.append("API returned 5xx")
        if query in REQUIRED_PARSED and not parsed_items:
            query_errors.append("parsed_items_count=0")
        if query == "???" and _is_misleading_empty_plan(data):
            query_errors.append("garbage query returned misleading plan")
        if query == "???" and parsed_items:
            query_errors.append("garbage query parsed unexpected items")

        if query_errors:
            errors.extend(f"{query}: {error}" for error in query_errors)
        if query == "兩包麵 一包薯條 四包薯片 油 糖 M&M":
            missing_ok = {"M&M", "薯條"} & {str(item.get("keyword")) for item in parsed_items}
            if not missing_ok:
                warnings.append("Real-user mixed query parsed, but M&M/薯條 availability may depend on data.")

        checks.append(
            {
                "query": query,
                "ok": not query_errors and status_code < 400,
                "status_code": status_code,
                "parsed_items_count": len(parsed_items),
                "plans_count": len(plans),
                "warnings": data.get("warnings") or [],
                "recommended_plan_type": data.get("recommended_plan_type"),
            }
        )

    return {
        "ok": not errors and all(check["ok"] for check in checks),
        "basket_checks": checks,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-check real user basket queries through /api/basket/ask.")
    parser.add_argument("--base-url", default="", help="Optional running API base URL. Defaults to in-process TestClient.")
    parser.add_argument("--point-code", default="p001")
    parser.add_argument("--date", default="latest")
    args = parser.parse_args()

    summary = run_smoke(base_url=args.base_url, point_code=args.point_code, date=args.date)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
