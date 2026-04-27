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


def test_get_user_watchlist(store_path):
    response = client.get("/api/user/watchlist", params={"user_token": "demo-user-token"})

    assert response.status_code == 200
    assert response.json() == {"user_token": "demo-user-token", "items": []}


def test_post_user_watchlist(store_path):
    response = client.post(
        "/api/user/watchlist",
        json={
            "user_token": "demo-user-token",
            "item": {
                "product_oid": 659,
                "product_name": "Rice",
                "package_quantity": "1kg",
                "category_name": "Rice",
                "point_code": "p001",
                "point_name": "Point",
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["product_oid"] == 659


def test_delete_user_watchlist_item(store_path):
    client.post(
        "/api/user/watchlist",
        json={"user_token": "demo-user-token", "item": {"product_oid": 659, "point_code": "p001"}},
    )

    response = client.delete(
        "/api/user/watchlist/659",
        params={"user_token": "demo-user-token", "point_code": "p001"},
    )

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_delete_nonexistent_user_watchlist_item_warns(store_path):
    response = client.delete(
        "/api/user/watchlist/404",
        params={"user_token": "demo-user-token", "point_code": "p001"},
    )

    assert response.status_code == 200
    assert response.json()["warning"] == "Watchlist item not found."


def test_missing_user_token_returns_400(store_path):
    response = client.get("/api/user/watchlist", params={"user_token": ""})

    assert response.status_code in {400, 422}
