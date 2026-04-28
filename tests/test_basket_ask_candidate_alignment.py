from pathlib import Path

import pytest

pytest.importorskip("fastapi")
testclient = pytest.importorskip("fastapi.testclient")
TestClient = testclient.TestClient

import app.api as api
from app.main import app
from services.simple_basket_parser import parse_simple_basket_text

client = TestClient(app)


def _patch_api_with_parser_result(monkeypatch):
    def fake_build_result(date, point_code, text, processed_root, selected_products=None):
        parsed_items = [
            {"keyword": item["keyword"], "quantity": item.get("quantity", 1)}
            for item in parse_simple_basket_text(text)
        ]
        if not parsed_items:
            return {
                "date": date,
                "point_code": point_code,
                "parsed_items": [],
                "plans": [],
                "warnings": ["未能識別購物清單，請輸入商品名稱，例如：米、洗頭水、紙巾。"],
                "recommended_plan_type": None,
                "recommendation_reason": "請輸入商品名稱，例如：米、洗頭水、紙巾。",
            }
        return {
            "date": date,
            "point_code": point_code,
            "parsed_items": parsed_items,
            "plans": [
                {
                    "plan_type": "partial_best_effort",
                    "items": [{"keyword": item["keyword"], "matched": True} for item in parsed_items],
                    "matched_items": [{"keyword": item["keyword"]} for item in parsed_items],
                    "unmatched_items": [],
                    "estimated_total_mop": 10.0,
                    "store_count": 1,
                    "stores": [],
                    "is_partial": False,
                }
            ],
            "warnings": [],
            "recommended_plan_type": "partial_best_effort",
            "recommendation_reason": "Best effort.",
        }

    monkeypatch.setattr(api, "is_sqlite_provider_enabled", lambda: False)
    monkeypatch.setattr(api, "get_processed_root", lambda: Path("processed"))
    monkeypatch.setattr(api, "resolve_date", lambda date, processed_root=None: "2026-04-28")
    monkeypatch.setattr(api, "resolve_point_from_request", lambda *args, **kwargs: {"point_code": "p001"})
    monkeypatch.setattr(api, "ensure_processed_data_exists", lambda *args, **kwargs: None)
    monkeypatch.setattr(api, "build_result", fake_build_result)


@pytest.mark.parametrize("query", ["糖", "朱古力", "麵"])
def test_basket_ask_parses_single_candidate_keywords(monkeypatch, query):
    _patch_api_with_parser_result(monkeypatch)
    response = client.post("/api/basket/ask", json={"text": query, "point_code": "p001", "date": "latest"})
    assert response.status_code == 200
    data = response.json()
    assert data["parsed_items"]
    assert data["parsed_items"][0]["keyword"] == query
    assert len(data["plans"]) >= 1


def test_basket_ask_parses_space_separated_candidate_keywords(monkeypatch):
    _patch_api_with_parser_result(monkeypatch)
    response = client.post("/api/basket/ask", json={"text": "糖 朱古力 麵", "point_code": "p001", "date": "latest"})
    assert response.status_code == 200
    data = response.json()
    assert [item["keyword"] for item in data["parsed_items"]] == ["糖", "朱古力", "麵"]
    assert len(data["plans"]) >= 1


def test_basket_ask_garbage_has_no_misleading_plan(monkeypatch):
    _patch_api_with_parser_result(monkeypatch)
    response = client.post("/api/basket/ask", json={"text": "???", "point_code": "p001", "date": "latest"})
    assert response.status_code == 200
    data = response.json()
    assert data["parsed_items"] == []
    assert data["plans"] == []
    assert data["recommended_plan_type"] is None
    assert "未能識別購物清單" in data["warnings"][0]


@pytest.mark.parametrize("query", ["洗頭水", "洗衣液", "米", "紙巾"])
def test_existing_simple_mode_keywords_still_parse(monkeypatch, query):
    _patch_api_with_parser_result(monkeypatch)
    response = client.post("/api/basket/ask", json={"text": query, "point_code": "p001", "date": "latest"})
    assert response.status_code == 200
    assert response.json()["parsed_items"][0]["keyword"] == query
