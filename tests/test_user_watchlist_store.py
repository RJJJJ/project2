from __future__ import annotations

import json

from services import user_watchlist_store as store


def _item(product_oid: int = 659, point_code: str = "p001") -> dict:
    return {
        "product_oid": product_oid,
        "product_name": "Rice",
        "package_quantity": "1kg",
        "category_name": "Rice",
        "point_code": point_code,
        "point_name": "Point",
    }


def test_store_file_missing_initializes(tmp_path):
    path = tmp_path / "watchlists.json"

    data = store.load_store(path)

    assert data == {"users": {}}
    assert path.exists()


def test_add_watchlist_item(tmp_path):
    result = store.add_watchlist_item("demo-user-token", _item(), tmp_path / "watchlists.json")

    assert result["items"][0]["product_oid"] == 659
    assert result["items"][0]["point_code"] == "p001"
    assert result["items"][0]["added_at"]


def test_duplicate_product_point_does_not_duplicate(tmp_path):
    path = tmp_path / "watchlists.json"
    store.add_watchlist_item("demo-user-token", _item(), path)
    result = store.add_watchlist_item("demo-user-token", {**_item(), "product_name": "Updated"}, path)

    assert len(result["items"]) == 1
    assert result["items"][0]["product_name"] == "Updated"
    assert result["warning"]


def test_remove_watchlist_item(tmp_path):
    path = tmp_path / "watchlists.json"
    store.add_watchlist_item("demo-user-token", _item(), path)

    result = store.remove_watchlist_item("demo-user-token", 659, "p001", path)

    assert result["items"] == []
    assert result["warning"] is None


def test_remove_nonexistent_item_does_not_crash(tmp_path):
    result = store.remove_watchlist_item("demo-user-token", 404, "p001", tmp_path / "watchlists.json")

    assert result["items"] == []
    assert result["warning"] == "Watchlist item not found."


def test_set_alert_status(tmp_path):
    result = store.set_alert_status(
        "demo-user-token",
        {
            "alert_id": "p001:659:near_historical_low:2026-04-27",
            "product_oid": 659,
            "point_code": "p001",
            "alert_type": "near_historical_low",
            "status": "viewed",
        },
        tmp_path / "watchlists.json",
    )

    assert result["alert_history"][0]["status"] == "viewed"
    assert result["alert_history"][0]["updated_at"]


def test_duplicate_alert_id_updates_status(tmp_path):
    path = tmp_path / "watchlists.json"
    alert = {
        "alert_id": "p001:659:near_historical_low:2026-04-27",
        "product_oid": 659,
        "point_code": "p001",
        "alert_type": "near_historical_low",
        "status": "viewed",
    }
    store.set_alert_status("demo-user-token", alert, path)
    result = store.set_alert_status("demo-user-token", {**alert, "status": "dismissed"}, path)

    assert len(result["alert_history"]) == 1
    assert result["alert_history"][0]["status"] == "dismissed"


def test_clear_alert_history(tmp_path):
    path = tmp_path / "watchlists.json"
    store.set_alert_status(
        "demo-user-token",
        {"alert_id": "a1", "product_oid": 1, "point_code": "p001", "alert_type": "below_average", "status": "viewed"},
        path,
    )

    result = store.clear_alert_history("demo-user-token", path)

    assert result["alert_history"] == []
    assert store.get_alert_history("demo-user-token", path) == []


def test_atomic_save_writes_json_and_removes_temp(tmp_path):
    path = tmp_path / "nested" / "watchlists.json"

    store.save_store({"users": {"demo": {"watchlist": [], "alert_history": []}}}, path)

    assert json.loads(path.read_text(encoding="utf-8"))["users"]["demo"]["watchlist"] == []
    assert not path.with_name(f"{path.name}.tmp").exists()
