from __future__ import annotations

from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
testclient = pytest.importorskip("fastapi.testclient")
HTTPException = fastapi.HTTPException
TestClient = testclient.TestClient

import app.api as api
from app.main import app


client = TestClient(app)


def test_watchlist_signals_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(api, "get_processed_root", lambda: Path("demo_data/processed"))
    monkeypatch.setattr(api, "resolve_point_from_request", lambda **kwargs: {"point_code": "p001"})
    monkeypatch.setattr(
        api,
        "analyze_watchlist_items",
        lambda *args, **kwargs: {
            "point_code": "p001",
            "date": "2026-04-27",
            "items": [{"product_oid": 659, "current_min_price_mop": 13.5}],
            "warnings": [],
        },
    )

    response = client.post(
        "/api/watchlist/signals",
        json={
            "point_code": "p001",
            "date": "latest",
            "lookback_days": 30,
            "items": [{"product_oid": 659, "product_name": "Rice"}],
        },
    )

    assert response.status_code == 200
    assert response.json()["items"] == [{"product_oid": 659, "current_min_price_mop": 13.5}]


def test_watchlist_signals_empty_items(monkeypatch) -> None:
    monkeypatch.setattr(api, "get_processed_root", lambda: Path("demo_data/processed"))
    monkeypatch.setattr(api, "resolve_point_from_request", lambda **kwargs: {"point_code": "p001"})
    monkeypatch.setattr(
        api,
        "analyze_watchlist_items",
        lambda *args, **kwargs: {"point_code": "p001", "date": "2026-04-27", "items": [], "warnings": []},
    )

    response = client.post("/api/watchlist/signals", json={"point_code": "p001", "items": []})

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_watchlist_signals_invalid_date_does_not_500(monkeypatch) -> None:
    monkeypatch.setattr(api, "get_processed_root", lambda: Path("demo_data/processed"))
    monkeypatch.setattr(api, "resolve_point_from_request", lambda **kwargs: {"point_code": "p001"})
    monkeypatch.setattr(
        api,
        "analyze_watchlist_items",
        lambda *args, **kwargs: {
            "point_code": "p001",
            "date": "not-a-date",
            "items": [{"product_oid": 659, "warnings": ["今日無價格資料。"]}],
            "warnings": [],
        },
    )

    response = client.post(
        "/api/watchlist/signals",
        json={"point_code": "p001", "date": "not-a-date", "items": [{"product_oid": 659}]},
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["warnings"]


def test_watchlist_signals_invalid_point_does_not_500(monkeypatch) -> None:
    def raise_not_found(**kwargs):
        raise HTTPException(status_code=404, detail="Collection point not found")

    monkeypatch.setattr(api, "resolve_point_from_request", raise_not_found)

    response = client.post(
        "/api/watchlist/signals",
        json={"point_code": "bad-point", "items": [{"product_oid": 659}]},
    )

    assert response.status_code == 404
