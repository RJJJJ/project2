
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


def test_get_product_candidates(monkeypatch) -> None:
    monkeypatch.setattr(api, "get_processed_root", lambda: Path("processed"))
    monkeypatch.setattr(api, "resolve_date", lambda date, processed_root=None: "2026-04-25")
    monkeypatch.setattr(api, "resolve_point_from_request", lambda **kwargs: {"point_code": "p001"})
    monkeypatch.setattr(api, "ensure_processed_data_exists", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        api,
        "search_product_candidates",
        lambda *args, **kwargs: [
            {
                "keyword": "?",
                "matched_alias": "?",
                "product_oid": 101,
                "product_name": "?????",
                "package_quantity": "1??",
                "category_name": "??",
                "min_price_mop": 13.5,
                "max_price_mop": 18.0,
                "store_count": 2,
                "sample_supermarkets": ["Store A"],
                "score": 170.65,
                "is_recommended": True,
                "recommendation_reason": "??????????????",
                "ranking_factors": {
                    "match_score": 120,
                    "coverage_score": 10,
                    "package_preference_score": 40,
                    "price_score": 0.65,
                    "final_score": 170.65,
                },
            }
        ],
    )

    response = client.get("/api/products/candidates?keyword=?&point_code=p001&date=latest&limit=8")

    assert response.status_code == 200
    assert response.json()["date"] == "2026-04-25"
    assert response.json()["point_code"] == "p001"
    assert response.json()["keyword"] == "?"
    assert response.json()["candidates"][0]["product_oid"] == 101
    assert response.json()["candidates"][0]["is_recommended"] is True
    assert "final_score" in response.json()["candidates"][0]["ranking_factors"]


def test_get_product_candidates_empty(monkeypatch) -> None:
    monkeypatch.setattr(api, "get_processed_root", lambda: Path("processed"))
    monkeypatch.setattr(api, "resolve_date", lambda date, processed_root=None: "2026-04-25")
    monkeypatch.setattr(api, "resolve_point_from_request", lambda **kwargs: {"point_code": "p001"})
    monkeypatch.setattr(api, "ensure_processed_data_exists", lambda *args, **kwargs: None)
    monkeypatch.setattr(api, "search_product_candidates", lambda *args, **kwargs: [])

    response = client.get("/api/products/candidates?keyword=???&point_code=p001")

    assert response.status_code == 200
    assert response.json()["candidates"] == []


def test_get_product_candidates_invalid_point(monkeypatch) -> None:
    monkeypatch.setattr(api, "get_processed_root", lambda: Path("processed"))
    monkeypatch.setattr(api, "resolve_date", lambda date, processed_root=None: "2026-04-25")

    def raise_not_found(**kwargs):
        raise HTTPException(status_code=404, detail="Collection point not found: bad")

    monkeypatch.setattr(api, "resolve_point_from_request", raise_not_found)

    response = client.get("/api/products/candidates?keyword=?&point_code=bad")

    assert response.status_code == 404
    assert "Collection point not found" in response.json()["detail"]


def test_get_product_candidates_invalid_date(monkeypatch) -> None:
    monkeypatch.setattr(api, "get_processed_root", lambda: Path("processed"))
    monkeypatch.setattr(api, "resolve_date", lambda date, processed_root=None: "2026-04-25")
    monkeypatch.setattr(api, "resolve_point_from_request", lambda **kwargs: {"point_code": "p001"})

    def raise_missing(*args, **kwargs):
        raise HTTPException(status_code=404, detail="Processed data not found")

    monkeypatch.setattr(api, "ensure_processed_data_exists", raise_missing)

    response = client.get("/api/products/candidates?keyword=?&point_code=p001&date=missing")

    assert response.status_code == 404
    assert "Processed data not found" in response.json()["detail"]
