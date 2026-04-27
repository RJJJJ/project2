from __future__ import annotations

import pytest

testclient = pytest.importorskip("fastapi.testclient")
TestClient = testclient.TestClient

from app.main import app
from services import user_watchlist_store


client = TestClient(app)


@pytest.fixture()
def store_path(tmp_path, monkeypatch):
    path = tmp_path / "watchlists.json"
    monkeypatch.setattr(user_watchlist_store, "DEFAULT_STORE_PATH", path)
    return path


def test_get_alert_history(store_path):
    response = client.get("/api/user/alert-history", params={"user_token": "demo-user-token"})

    assert response.status_code == 200
    assert response.json() == {"user_token": "demo-user-token", "alert_history": []}


def test_post_alert_status(store_path):
    response = client.post(
        "/api/user/alert-history",
        json={
            "user_token": "demo-user-token",
            "alert": {
                "alert_id": "p001:659:near_historical_low:2026-04-27",
                "product_oid": 659,
                "point_code": "p001",
                "alert_type": "near_historical_low",
                "status": "viewed",
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["alert_history"][0]["status"] == "viewed"


def test_delete_alert_history(store_path):
    client.post(
        "/api/user/alert-history",
        json={"user_token": "demo-user-token", "alert": {"alert_id": "a1", "status": "viewed"}},
    )

    response = client.delete("/api/user/alert-history", params={"user_token": "demo-user-token"})

    assert response.status_code == 200
    assert response.json()["alert_history"] == []


def test_missing_user_token_returns_400(store_path):
    response = client.get("/api/user/alert-history", params={"user_token": ""})

    assert response.status_code in {400, 422}
