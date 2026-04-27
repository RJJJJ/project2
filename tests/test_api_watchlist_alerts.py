from __future__ import annotations

from pathlib import Path

import pytest

testclient = pytest.importorskip("fastapi.testclient")
TestClient = testclient.TestClient

import app.api as api
from app.main import app


client = TestClient(app)


def test_watchlist_alerts_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(api, "get_processed_root", lambda: Path("demo_data/processed"))
    monkeypatch.setattr(api, "resolve_point_from_request", lambda **kwargs: {"point_code": "p001"})
    monkeypatch.setattr(
        api,
        "generate_watchlist_alerts",
        lambda *args, **kwargs: {
            "point_code": "p001",
            "date": "2026-04-27",
            "alerts": [{"product_oid": 659, "alert_type": "near_historical_low"}],
            "summary": {"items_count": 1, "alerts_count": 1, "notify_count": 1},
            "warnings": [],
        },
    )

    response = client.post(
        "/api/watchlist/alerts",
        json={"point_code": "p001", "items": [{"product_oid": 659, "product_name": "Rice"}]},
    )

    assert response.status_code == 200
    assert response.json()["alerts"][0]["alert_type"] == "near_historical_low"
    assert "summary" in response.json()


def test_watchlist_alerts_empty_items(monkeypatch) -> None:
    monkeypatch.setattr(api, "get_processed_root", lambda: Path("demo_data/processed"))
    monkeypatch.setattr(api, "resolve_point_from_request", lambda **kwargs: {"point_code": "p001"})
    monkeypatch.setattr(
        api,
        "generate_watchlist_alerts",
        lambda *args, **kwargs: {
            "point_code": "p001",
            "date": "2026-04-27",
            "alerts": [],
            "summary": {"items_count": 0, "alerts_count": 0, "notify_count": 0},
            "warnings": [],
        },
    )

    response = client.post("/api/watchlist/alerts", json={"point_code": "p001", "items": []})

    assert response.status_code == 200
    assert response.json()["alerts"] == []
    assert response.json()["summary"]["items_count"] == 0


def test_watchlist_alerts_invalid_product_does_not_500(monkeypatch) -> None:
    monkeypatch.setattr(api, "get_processed_root", lambda: Path("demo_data/processed"))
    monkeypatch.setattr(api, "resolve_point_from_request", lambda **kwargs: {"point_code": "p001"})
    monkeypatch.setattr(
        api,
        "generate_watchlist_alerts",
        lambda *args, **kwargs: {
            "point_code": "p001",
            "date": "2026-04-27",
            "alerts": [],
            "summary": {"items_count": 1, "alerts_count": 0, "notify_count": 0},
            "warnings": [],
            "item_warnings": [{"product_oid": 404, "warnings": ["今日無價格資料。"]}],
        },
    )

    response = client.post("/api/watchlist/alerts", json={"point_code": "p001", "items": [{"product_oid": 404}]})

    assert response.status_code == 200
    assert response.json()["alerts"] == []
    assert response.json()["item_warnings"]
