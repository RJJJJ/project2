from __future__ import annotations

from pathlib import Path

import pytest

testclient = pytest.importorskip("fastapi.testclient")
TestClient = testclient.TestClient

import app.api as api
from app.main import app


client = TestClient(app)


def test_historical_signals_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(api, "get_processed_root", lambda: Path("demo_data/processed"))
    monkeypatch.setattr(api, "resolve_point_from_request", lambda **kwargs: {"point_code": "p001"})
    monkeypatch.setattr(
        api,
        "analyze_historical_price_signals",
        lambda *args, **kwargs: {
            "point_code": "p001",
            "current_date": "2026-04-27",
            "lookback_days": 30,
            "signals": [{"product_oid": 100}],
            "summary": {"signals_count": 1},
            "warnings": [],
        },
    )

    response = client.get("/api/historical-signals/p001?date=latest&lookback_days=30&top_n=5")

    assert response.status_code == 200
    assert response.json()["signals"] == [{"product_oid": 100}]


def test_historical_signals_returns_200_with_warnings_when_history_is_insufficient(monkeypatch) -> None:
    monkeypatch.setattr(api, "get_processed_root", lambda: Path("demo_data/processed"))
    monkeypatch.setattr(api, "resolve_point_from_request", lambda **kwargs: {"point_code": "p001"})
    monkeypatch.setattr(
        api,
        "analyze_historical_price_signals",
        lambda *args, **kwargs: {
            "point_code": "p001",
            "current_date": "2026-04-27",
            "lookback_days": 30,
            "signals": [],
            "summary": {"signals_count": 0},
            "warnings": ["Not enough historical dates for historical comparison."],
        },
    )

    response = client.get("/api/historical-signals/p001")

    assert response.status_code == 200
    assert response.json()["signals"] == []
    assert response.json()["warnings"]


def test_historical_signals_invalid_date_does_not_500(monkeypatch) -> None:
    monkeypatch.setattr(api, "get_processed_root", lambda: Path("demo_data/processed"))
    monkeypatch.setattr(api, "resolve_point_from_request", lambda **kwargs: {"point_code": "p001"})
    monkeypatch.setattr(
        api,
        "analyze_historical_price_signals",
        lambda *args, **kwargs: {
            "point_code": "p001",
            "current_date": "not-a-date",
            "lookback_days": 30,
            "signals": [],
            "summary": {"signals_count": 0},
            "warnings": ["Not enough historical dates for historical comparison."],
        },
    )

    response = client.get("/api/historical-signals/p001?date=not-a-date")

    assert response.status_code == 200
    assert response.json()["warnings"]
