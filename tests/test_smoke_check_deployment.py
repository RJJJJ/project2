from __future__ import annotations

import requests

from scripts.smoke_check_deployment import build_checks, exit_code_for_summary, run_smoke_checks


class FakeResponse:
    def __init__(self, status_code: int, text: str = "OK"):
        self.status_code = status_code
        self.text = text


class FakeSession:
    def __init__(self, status_codes: list[int]):
        self.status_codes = status_codes
        self.calls: list[dict] = []

    def request(self, method, url, params=None, json=None, timeout=None):
        self.calls.append(
            {
                "method": method,
                "url": url,
                "params": params,
                "json": json,
                "timeout": timeout,
            }
        )
        return FakeResponse(self.status_codes[len(self.calls) - 1])


class FailingOnceSession(FakeSession):
    def request(self, method, url, params=None, json=None, timeout=None):
        if not self.calls:
            self.calls.append({"method": method, "url": url, "params": params, "json": json, "timeout": timeout})
            raise requests.Timeout("timed out")
        return super().request(method, url, params=params, json=json, timeout=timeout)


def test_build_checks_includes_required_endpoints():
    checks = build_checks(point_code="p001", keyword="米")

    assert [check.name for check in checks] == [
        "health",
        "points",
        "product_candidates",
        "historical_signals",
        "watchlist_signals",
        "watchlist_alerts",
        "basket_ask",
    ]
    assert checks[2].params["keyword"] == "米"
    assert checks[4].json_body["point_code"] == "p001"


def test_failed_endpoint_does_not_interrupt_all_checks():
    session = FakeSession([200, 500, 200, 200, 200, 200, 200])

    summary = run_smoke_checks("https://example.test", session=session, timeout=7)

    assert summary["ok"] is False
    assert len(summary["checks"]) == 7
    assert len(session.calls) == 7
    assert summary["checks"][1]["ok"] is False
    assert summary["checks"][1]["status_code"] == 500
    assert summary["errors"] == ["points: HTTP 500: OK"]
    assert all(call["timeout"] == 7 for call in session.calls)


def test_request_exception_is_collected_and_remaining_checks_continue():
    session = FailingOnceSession([200, 200, 200, 200, 200, 200, 200])

    summary = run_smoke_checks("https://example.test", session=session)

    assert summary["ok"] is False
    assert len(summary["checks"]) == 7
    assert summary["checks"][0]["error"] == "timed out"
    assert "health: timed out" in summary["errors"]


def test_exit_code_for_summary():
    assert exit_code_for_summary({"ok": True}) == 0
    assert exit_code_for_summary({"ok": False}) == 1
