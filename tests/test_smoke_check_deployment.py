from __future__ import annotations

import requests

from scripts.smoke_check_deployment import build_checks, exit_code_for_summary, run_smoke_checks


class FakeResponse:
    def __init__(self, status_code: int, payload=None, text: str = "OK"):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeSession:
    def __init__(self, responses: list[FakeResponse]):
        self.responses = responses
        self.calls: list[dict] = []

    def request(self, method, url, params=None, json=None, timeout=None):
        self.calls.append({"method": method, "url": url, "params": params, "json": json, "timeout": timeout})
        return self.responses[len(self.calls) - 1]


class FailingBasketSession(FakeSession):
    def request(self, method, url, params=None, json=None, timeout=None):
        if url.endswith("api/basket/ask"):
            self.calls.append({"method": method, "url": url, "params": params, "json": json, "timeout": timeout})
            raise requests.Timeout("timed out")
        return super().request(method, url, params=params, json=json, timeout=timeout)


def success_responses():
    return [
        FakeResponse(200, {"ok": True}),
        FakeResponse(200, [{"point_code": f"p{i:03d}"} for i in range(1, 16)]),
        FakeResponse(200, {"candidates": [{"name": "米"}]}),
        FakeResponse(200, {"answer": "demo"}),
    ]


def test_build_checks_includes_required_endpoints():
    checks = build_checks(point_code="p001", keyword="米")

    assert [check.name for check in checks] == ["health", "points_15", "product_candidates", "basket_ask"]
    assert checks[2].params == {"keyword": "米", "point_code": "p001", "date": "latest"}
    assert checks[3].json_body["text"] == "我想買一包米、兩支洗頭水、一包紙巾"


def test_health_success():
    session = FakeSession(success_responses())

    summary = run_smoke_checks("https://example.test", session=session, timeout=7)

    assert summary["ok"] is True
    assert summary["checks"][0] == {"name": "health", "ok": True, "status_code": 200}
    assert all(call["timeout"] == 7 for call in session.calls)


def test_points_less_than_15_fails():
    responses = success_responses()
    responses[1] = FakeResponse(200, [{"point_code": "p001"}])
    session = FakeSession(responses)

    summary = run_smoke_checks("https://example.test", session=session)

    assert summary["ok"] is False
    assert summary["checks"][1]["points_count"] == 1
    assert "points_15: Expected at least 15 points, got 1" in summary["errors"]


def test_candidates_fail():
    responses = success_responses()
    responses[2] = FakeResponse(500, {"error": "boom"}, text="boom")
    session = FakeSession(responses)

    summary = run_smoke_checks("https://example.test", session=session)

    assert summary["ok"] is False
    assert summary["checks"][2]["status_code"] == 500
    assert "product_candidates: HTTP 500: boom" in summary["errors"]


def test_basket_fail():
    session = FailingBasketSession(success_responses())

    summary = run_smoke_checks("https://example.test", session=session)

    assert summary["ok"] is False
    assert summary["checks"][3]["error"] == "timed out"
    assert "basket_ask: timed out" in summary["errors"]


def test_exit_code_for_summary():
    assert exit_code_for_summary({"ok": True}) == 0
    assert exit_code_for_summary({"ok": False}) == 1
