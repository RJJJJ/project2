from __future__ import annotations

from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
testclient = pytest.importorskip("fastapi.testclient")
TestClient = testclient.TestClient

import app.api as api
from app.main import app
from services.sqlite_store import connect_db, init_db, upsert_collection_points

client = TestClient(app)

RICE = "\u7c73"
SHAMPOO = "\u6d17\u982d\u6c34"
TISSUE = "\u7d19\u5dfe"


def _seed_db(db_path: Path) -> None:
    with connect_db(db_path) as conn:
        init_db(conn)
        upsert_collection_points(conn, [{"point_code": "p001", "name": "\u9ad8\u58eb\u5fb7", "district": "\u6fb3\u9580\u534a\u5cf6", "lat": 22.1, "lng": 113.5, "dst": 500}])
        conn.executemany("INSERT INTO supermarkets(supermarket_oid, supermarket_name) VALUES (?, ?)", [("s1", "Store A"), ("s2", "Store B")])
        conn.executemany(
            "INSERT INTO products(product_oid, product_name, package_quantity, category_id, category_name) VALUES (?, ?, ?, ?, ?)",
            [
                ("rice", "\u5bcc\u58eb\u73cd\u73e0\u7c73", "5\u516c\u65a4", 1, "\u7c73\u985e"),
                ("shampoo", "\u6f58\u5a77\u6d17\u9aee\u9732", "700ml", 10, "\u500b\u4eba\u8b77\u7406"),
                ("tissue", "Tempo \u76d2\u88dd\u7d19\u5dfe", "5\u76d2", 15, "\u885b\u751f\u7d19"),
            ],
        )
        conn.executemany(
            "INSERT INTO price_records(date, point_code, supermarket_oid, product_oid, price_mop, category_id, source_file) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                ("2026-04-28", "p001", "s1", "rice", 50.0, 1, "category_1_prices.jsonl"),
                ("2026-04-28", "p001", "s1", "shampoo", 35.0, 10, "category_10_prices.jsonl"),
                ("2026-04-28", "p001", "s2", "tissue", 20.0, 15, "category_15_prices.jsonl"),
            ],
        )
        conn.commit()


def _enable_sqlite(monkeypatch, db_path: Path) -> None:
    monkeypatch.setenv("PROJECT2_DATA_PROVIDER", "sqlite")
    monkeypatch.setenv("PROJECT2_SQLITE_DB_PATH", str(db_path))
    monkeypatch.setattr(api, "resolve_point_from_request", lambda *args, **kwargs: {"point_code": "p001", "name": "\u9ad8\u58eb\u5fb7"})


def test_products_candidates_uses_sqlite_provider(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "test.sqlite3"
    _seed_db(db_path)
    _enable_sqlite(monkeypatch, db_path)

    response = client.get(f"/api/products/candidates?point_code=p001&keyword={RICE}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["date"] == "2026-04-28"
    assert payload["candidates"][0]["product_oid"] == "rice"


def test_products_candidates_sqlite_missing_db_returns_503(monkeypatch, tmp_path: Path) -> None:
    _enable_sqlite(monkeypatch, tmp_path / "missing.sqlite3")

    response = client.get(f"/api/products/candidates?point_code=p001&keyword={RICE}")

    assert response.status_code == 503
    assert "SQLite provider enabled but database not found" in response.json()["detail"]


def test_basket_ask_sqlite_missing_db_returns_503(monkeypatch, tmp_path: Path) -> None:
    _enable_sqlite(monkeypatch, tmp_path / "missing.sqlite3")

    response = client.post("/api/basket/ask", json={"text": RICE, "point_code": "p001"})

    assert response.status_code == 503


def test_basket_ask_sqlite_returns_compatible_schema(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "test.sqlite3"
    _seed_db(db_path)
    _enable_sqlite(monkeypatch, db_path)

    response = client.post("/api/basket/ask", json={"text": f"{RICE}\u3001{SHAMPOO}\u3001{TISSUE}", "point_code": "p001"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["recommended_plan_type"] == "sqlite_simple_basket"
    assert payload["plans"][0]["estimated_total_mop"] == 105.0
    assert payload["plans"][0]["store_count"] == 2
    assert len(payload["parsed_items"]) == 3


def test_jsonl_provider_does_not_require_sqlite_db(monkeypatch) -> None:
    monkeypatch.delenv("PROJECT2_DATA_PROVIDER", raising=False)
    monkeypatch.delenv("PROJECT2_SQLITE_DB_PATH", raising=False)
    monkeypatch.setattr(api, "resolve_point_from_request", lambda *args, **kwargs: {"point_code": "p001"})
    monkeypatch.setattr(api, "get_processed_root", lambda: Path("processed"))
    monkeypatch.setattr(api, "resolve_date", lambda date, processed_root=None: "2026-04-28")
    monkeypatch.setattr(api, "ensure_processed_data_exists", lambda *args, **kwargs: None)
    monkeypatch.setattr(api, "search_product_candidates", lambda *args, **kwargs: [{"product_oid": "jsonl"}])

    response = client.get(f"/api/products/candidates?point_code=p001&keyword={RICE}")

    assert response.status_code == 200
    assert response.json()["candidates"] == [{"product_oid": "jsonl"}]
