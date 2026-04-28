from pathlib import Path

from fastapi.testclient import TestClient

import app.api as api
from app.main import app
from services.shopping_agent_orchestrator import run_shopping_agent


FAKE_PRODUCTS = [
    {"product_oid": "1", "product_name": "太古純正砂糖", "category_id": 5, "category_name": "調味料"},
    {"product_oid": "2", "product_name": "維他奶低糖豆奶", "category_id": 6, "category_name": "飲品"},
    {"product_oid": "3", "product_name": "獅球嘜花生油", "category_id": 3, "category_name": "食用油"},
    {"product_oid": "4", "product_name": "男士去屑洗髮乳", "category_id": 10, "category_name": "個人護理"},
    {"product_oid": "5", "product_name": "樂事薯片", "category_id": 11, "category_name": "零食"},
    {"product_oid": "6", "product_name": "朱古力牛奶飲品", "category_id": 7, "category_name": "奶品"},
    {"product_oid": "7", "product_name": "高露潔牙膏", "category_id": 10, "category_name": "個人護理"},
]


def test_agent_real_user_query_needs_clarification(monkeypatch):
    monkeypatch.setattr("services.shopping_agent_orchestrator.load_products_from_sqlite", lambda db_path: FAKE_PRODUCTS)
    result = run_shopping_agent("兩包麵 一包薯條 四包薯片 油 糖 M&M", Path("missing.sqlite3"))
    assert result["status"] == "needs_clarification"
    assert {"麵", "油", "糖"} <= {item["raw_item_name"] for item in result["ambiguous_items"]}
    assert {"薯條", "M&M"} <= {item["raw_item_name"] for item in result["not_covered_items"]}
    resolved_by_name = {item["raw_item_name"]: item for item in result["resolved_items"]}
    assert resolved_by_name["薯片"]["intent_id"] == "chips"


def test_agent_specific_queries_resolve(monkeypatch):
    monkeypatch.setattr("services.shopping_agent_orchestrator.load_products_from_sqlite", lambda db_path: FAKE_PRODUCTS)
    result = run_shopping_agent("我想買砂糖同洗頭水", Path("missing.sqlite3"))
    assert result["status"] == "ok"
    assert {item["intent_id"] for item in result["resolved_items"]} == {"cooking_sugar", "shampoo"}

    result = run_shopping_agent("我想買食油、朱古力飲品、牙膏", Path("missing.sqlite3"))
    assert result["status"] == "ok"
    assert {item["intent_id"] for item in result["resolved_items"]} == {"cooking_oil", "chocolate_drink", "toothpaste"}


def test_agent_api_endpoint(monkeypatch):
    monkeypatch.setattr(api, "get_sqlite_db_path", lambda: Path("missing.sqlite3"))
    monkeypatch.setattr("services.shopping_agent_orchestrator.load_products_from_sqlite", lambda db_path: FAKE_PRODUCTS)
    response = TestClient(app).post("/api/agent/shopping", json={"query": "糖", "point_code": "p001", "use_llm": False})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "needs_clarification"
    assert data["ambiguous_items"][0]["raw_item_name"] == "糖"
