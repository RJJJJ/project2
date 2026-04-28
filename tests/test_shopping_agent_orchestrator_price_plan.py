from pathlib import Path

from services.shopping_agent_orchestrator import run_shopping_agent


FAKE_PRODUCTS = [
    {"product_oid": "p_sugar", "product_name": "太古純正砂糖", "category_id": 5, "category_name": "調味品"},
    {"product_oid": "p_shampoo", "product_name": "多芬深層修護洗髮乳", "category_id": 10, "category_name": "個人護理用品"},
    {"product_oid": "p_oil", "product_name": "刀嘜純正花生油", "category_id": 3, "category_name": "食油類"},
    {"product_oid": "p_chocolate_drink", "product_name": "吉百利朱古力飲品", "category_id": 6, "category_name": "飲品類"},
    {"product_oid": "p_toothpaste", "product_name": "高露潔牙膏", "category_id": 10, "category_name": "個人護理用品"},
    {"product_oid": "p_chips", "product_name": "樂事薯片", "category_id": 11, "category_name": "零食"},
]


def test_agent_price_plan_for_real_user_query_keeps_clarification(monkeypatch):
    monkeypatch.setattr("services.shopping_agent_orchestrator.load_products_from_sqlite", lambda db_path: FAKE_PRODUCTS)
    monkeypatch.setattr(
        "services.shopping_agent_price_adapter.plan_cheapest_by_product_candidates",
        lambda *args, **kwargs: {"status": "ok", "store_plans": [{"estimated_total_mop": 12}], "best_plan": {"estimated_total_mop": 12}, "warnings": [], "diagnostics": {"plan_count": 1}},
    )
    result = run_shopping_agent(
        "兩包麵 一包薯條 四包薯片 油 糖 M&M",
        Path("missing.sqlite3"),
        point_code="p001",
        include_price_plan=True,
    )
    assert result["status"] == "needs_clarification"
    assert result["price_plan"]["priceable_items"][0]["raw_item_name"] == "薯片"
    assert {"麵", "油", "糖"} <= {item["raw_item_name"] for item in result["ambiguous_items"]}


def test_agent_price_plan_for_specific_queries_no_crash(monkeypatch):
    monkeypatch.setattr("services.shopping_agent_orchestrator.load_products_from_sqlite", lambda db_path: FAKE_PRODUCTS)
    monkeypatch.setattr(
        "services.shopping_agent_price_adapter.plan_cheapest_by_product_candidates",
        lambda *args, **kwargs: {"status": "not_priceable", "store_plans": [], "best_plan": None, "warnings": ["no complete plan"], "diagnostics": {"plan_count": 0}},
    )
    for query in ["我想買砂糖同洗頭水", "我想買食油、朱古力飲品、牙膏"]:
        result = run_shopping_agent(query, Path("missing.sqlite3"), point_code="p001", include_price_plan=True)
        assert "price_plan" in result
        assert result["price_plan"]["diagnostics"]["priceable_item_count"] >= 1
        assert result["status"] in {"ok", "not_priceable"}
