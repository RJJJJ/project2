from __future__ import annotations

from fastapi import HTTPException
from fastapi.testclient import TestClient

import app.api as api
from app.main import app


client = TestClient(app)


def _sample_result() -> dict:
    return {
        "date": "2026-04-25",
        "point_code": "p001",
        "parsed_items": [{"keyword": "米", "quantity": 1}],
        "plans": [
            {
                "plan_type": "cheapest_by_item",
                "store_count": 1,
                "stores": [{"supermarket_oid": 1, "supermarket_name": "Store A"}],
                "items": [
                    {
                        "keyword": "米",
                        "requested_quantity": 1,
                        "product_name": "米",
                        "package_quantity": "1包",
                        "unit_price_mop": 10.0,
                        "subtotal_mop": 10.0,
                        "supermarket_name": "Store A",
                    }
                ],
                "estimated_total_mop": 10.0,
            }
        ],
        "warnings": [],
        "recommended_plan_type": "cheapest_by_item",
        "recommendation_reason": "lowest total",
    }


def test_health(monkeypatch) -> None:
    monkeypatch.setattr(api, "latest_processed_date", lambda: "2026-04-25")

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "latest_processed_date": "2026-04-25",
        "default_point_code": "p001",
    }


def test_points(monkeypatch) -> None:
    monkeypatch.setattr(api, "load_collection_points", lambda: [{"point_code": "p001", "name": "高士德"}])

    response = client.get("/api/points")

    assert response.status_code == 200
    assert response.json() == [{"point_code": "p001", "name": "高士德"}]


def test_basket_ask(monkeypatch) -> None:
    monkeypatch.setattr(api, "resolve_date", lambda date: "2026-04-25")
    monkeypatch.setattr(api, "resolve_point_from_request", lambda *args, **kwargs: {"point_code": "p001", "name": "高士德"})
    monkeypatch.setattr(api, "ensure_processed_data_exists", lambda date, point_code: None)
    monkeypatch.setattr(api, "build_result", lambda *args, **kwargs: _sample_result())

    response = client.post(
        "/api/basket/ask",
        json={"text": "我想買一包米", "point_code": "p001", "date": "latest"},
    )

    assert response.status_code == 200
    assert response.json()["parsed_items"] == [{"keyword": "米", "quantity": 1}]
    assert response.json()["recommended_plan_type"] == "cheapest_by_item"


def test_basket_ask_text(monkeypatch) -> None:
    monkeypatch.setattr(api, "resolve_date", lambda date: "2026-04-25")
    monkeypatch.setattr(api, "resolve_point_from_request", lambda *args, **kwargs: {"point_code": "p001", "name": "高士德"})
    monkeypatch.setattr(api, "ensure_processed_data_exists", lambda date, point_code: None)
    monkeypatch.setattr(api, "build_result", lambda *args, **kwargs: _sample_result())

    response = client.post(
        "/api/basket/ask_text",
        json={"text": "我想買一包米", "point_code": "p001", "date": "latest"},
    )

    assert response.status_code == 200
    assert "澳門採購決策建議" in response.json()["text"]


def test_signals(monkeypatch) -> None:
    monkeypatch.setattr(api, "resolve_date", lambda date: "2026-04-25")
    monkeypatch.setattr(api, "ensure_processed_data_exists", lambda date, point_code: None)
    monkeypatch.setattr(
        api,
        "analyze_point_signals",
        lambda *args, **kwargs: {
            "date": "2026-04-25",
            "point_code": "p001",
            "largest_price_gap": [{"product_name": f"product-{index}"} for index in range(10)],
        },
    )

    response = client.get("/api/signals/p001?top_n=5")

    assert response.status_code == 200
    assert len(response.json()["largest_price_gap"]) == 5


def test_point_not_found(monkeypatch) -> None:
    def raise_not_found(query: str) -> dict:
        raise HTTPException(status_code=404, detail=f"Collection point not found: {query}")

    monkeypatch.setattr(api, "_resolve_point_search", raise_not_found)

    response = client.get("/api/points/search?q=not-found")

    assert response.status_code == 404
