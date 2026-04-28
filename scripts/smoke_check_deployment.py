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
    return [
        SmokeCheck("health", "GET", "/api/health"),
        SmokeCheck("points_15", "GET", "/api/points"),
        SmokeCheck(
            "product_candidates",
            "GET",
            "/api/products/candidates",
            params={"keyword": keyword, "point_code": point_code, "date": "latest"},
        ),
        SmokeCheck(
            "basket_ask",
            "POST",
            "/api/basket/ask",
            json_body={
                "text": "我想買一包米、兩支洗頭水、一包紙巾",
                "point_code": point_code,
                "date": "latest",
            },
        ),
    ]


def _json_or_none(response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


def _points_count(payload: Any) -> int:
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        for key in ("points", "data", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return len(value)
    return 0


def _has_candidates(payload: Any) -> bool:
    if isinstance(payload, list):
        return True
    if isinstance(payload, dict):
        for key in ("candidates", "items", "products", "data"):
            if key in payload:
                return isinstance(payload[key], list)
    return False


def _has_basket_answer(payload: Any) -> bool:
    if isinstance(payload, dict):
        return any(key in payload for key in ("answer", "recommendation", "plans", "items", "summary"))
    return payload is not None


def validate_payload(check: SmokeCheck, payload: Any) -> tuple[bool, dict[str, Any], str | None]:
    if check.name == "points_15":
        count = _points_count(payload)
        return count >= 15, {"points_count": count}, None if count >= 15 else f"Expected at least 15 points, got {count}"
    if check.name == "product_candidates":
        ok = _has_candidates(payload)
        return ok, {}, None if ok else "Response did not look like a candidates payload"
    if check.name == "basket_ask":
        ok = _has_basket_answer(payload)
        return ok, {}, None if ok else "Response did not look like a basket answer"
    return True, {}, None


def run_check(session: requests.Session, base_url: str, check: SmokeCheck, timeout: int) -> dict[str, Any]:
    url = urljoin(normalize_base_url(base_url), check.path.lstrip("/"))
    result: dict[str, Any] = {"name": check.name, "ok": False, "status_code": None}
    try:
        response = session.request(check.method, url, params=check.params, json=check.json_body, timeout=timeout)
        result["status_code"] = response.status_code
        if not (200 <= response.status_code < 300):
            result["error"] = f"HTTP {response.status_code}: {response.text[:300]}"
            return result
        payload = _json_or_none(response)
        payload_ok, extra, payload_error = validate_payload(check, payload)
        result.update(extra)
        result["ok"] = payload_ok
        if payload_error:
            result["error"] = payload_error
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
    checks = [run_check(session, base_url, check, timeout) for check in build_checks(point_code=point_code, keyword=keyword)]
    errors = [f"{check['name']}: {check.get('error') or 'unknown error'}" for check in checks if not check["ok"]]
    return {"base_url": base_url.rstrip("/"), "ok": not errors, "checks": checks, "errors": errors, "warnings": []}


def exit_code_for_summary(summary: dict[str, Any]) -> int:
    return 0 if summary.get("ok") else 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke check deployed Project2 backend API.")
    parser.add_argument("--base-url", required=True, help="Backend base URL, e.g. https://macau-shopping-api.onrender.com")
    parser.add_argument("--point-code", default="p001")
    parser.add_argument("--keyword", default="米")
    parser.add_argument("--timeout", type=int, default=30)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = run_smoke_checks(args.base_url, point_code=args.point_code, keyword=args.keyword, timeout=args.timeout)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return exit_code_for_summary(summary)


if __name__ == "__main__":
    sys.exit(main())
