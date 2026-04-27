from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import requests


@dataclass(frozen=True)
class SmokeCheck:
    name: str
    method: str
    path: str
    params: dict[str, Any] | None = None
    json_body: dict[str, Any] | None = None


def normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/") + "/"


def build_checks(point_code: str = "p001", keyword: str = "米") -> list[SmokeCheck]:
    watchlist_items = [{"product_oid": 659, "product_name": "富士珍珠米"}]
    basket_payload = {
        "text": "我想買一包米、兩支洗頭水、一包紙巾",
        "point_code": point_code,
        "date": "latest",
    }
    watchlist_payload = {
        "point_code": point_code,
        "date": "latest",
        "lookback_days": 30,
        "items": watchlist_items,
    }
    return [
        SmokeCheck("health", "GET", "/api/health"),
        SmokeCheck("points", "GET", "/api/points"),
        SmokeCheck(
            "product_candidates",
            "GET",
            "/api/products/candidates",
            params={
                "keyword": keyword,
                "point_code": point_code,
                "date": "latest",
                "limit": 5,
            },
        ),
        SmokeCheck(
            "historical_signals",
            "GET",
            f"/api/historical-signals/{point_code}",
            params={"date": "latest", "lookback_days": 30, "top_n": 5},
        ),
        SmokeCheck("watchlist_signals", "POST", "/api/watchlist/signals", json_body=watchlist_payload),
        SmokeCheck("watchlist_alerts", "POST", "/api/watchlist/alerts", json_body=watchlist_payload),
        SmokeCheck("basket_ask", "POST", "/api/basket/ask", json_body=basket_payload),
    ]


def run_check(
    session: requests.Session,
    base_url: str,
    check: SmokeCheck,
    timeout: int,
) -> dict[str, Any]:
    url = urljoin(normalize_base_url(base_url), check.path.lstrip("/"))
    result = {
        "name": check.name,
        "ok": False,
        "status_code": None,
        "error": None,
    }
    try:
        response = session.request(
            check.method,
            url,
            params=check.params,
            json=check.json_body,
            timeout=timeout,
        )
        result["status_code"] = response.status_code
        if 200 <= response.status_code < 300:
            result["ok"] = True
        else:
            result["error"] = f"HTTP {response.status_code}: {response.text[:300]}"
    except requests.RequestException as exc:
        result["error"] = str(exc)
    return result


def run_smoke_checks(
    base_url: str,
    point_code: str = "p001",
    keyword: str = "米",
    timeout: int = 30,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    session = session or requests.Session()
    checks = [
        run_check(session, base_url, check, timeout)
        for check in build_checks(point_code=point_code, keyword=keyword)
    ]
    errors = [
        f"{check['name']}: {check['error'] or 'unknown error'}"
        for check in checks
        if not check["ok"]
    ]
    return {
        "base_url": base_url.rstrip("/"),
        "ok": not errors,
        "checks": checks,
        "errors": errors,
    }


def exit_code_for_summary(summary: dict[str, Any]) -> int:
    return 0 if summary.get("ok") else 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke check deployed Macau Shopping backend API.")
    parser.add_argument("--base-url", required=True, help="Backend base URL, e.g. https://macau-shopping-api.onrender.com")
    parser.add_argument("--point-code", default="p001")
    parser.add_argument("--keyword", default="米")
    parser.add_argument("--timeout", type=int, default=30)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = run_smoke_checks(
        base_url=args.base_url,
        point_code=args.point_code,
        keyword=args.keyword,
        timeout=args.timeout,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return exit_code_for_summary(summary)


if __name__ == "__main__":
    sys.exit(main())
