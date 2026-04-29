from pathlib import Path

from services.shopping_agent_orchestrator import run_shopping_agent


FAKE_PRODUCTS = [
    {"product_oid": "p_instant_noodle", "product_name": "\u516c\u4ed4\u7897\u9eb5", "category_id": 2, "category_name": "\u9eb5"},
    {"product_oid": "p_cooking_oil", "product_name": "\u7345\u7403\u569c\u7c9f\u7c73\u6cb9", "category_id": 3, "category_name": "\u6cb9"},
    {"product_oid": "p_cooking_sugar", "product_name": "\u592a\u53e4\u7d14\u6b63\u7802\u7cd6", "category_id": 5, "category_name": "\u7cd6"},
    {"product_oid": "p_chips", "product_name": "\u6a02\u4e8b\u85af\u7247", "category_id": 11, "category_name": "\u96f6\u98df"},
]

QUERY = "\u5169\u5305\u9eb5 \u4e00\u5305\u85af\u689d \u56db\u5305\u85af\u7247 \u6cb9 \u7cd6 M&M"


def _fake_planner(*args, **kwargs):
    return {
        "status": "ok",
        "store_plans": [
            {
                "supermarket_oid": "s001",
                "supermarket_name": "\u4f86\u4f86\u8d85\u5e02",
                "point_code": "p001",
                "store_count": 1,
                "estimated_total_mop": 33.8,
                "items": [
                    {
                        "raw_item_name": "\u85af\u7247",
                        "intent_id": "chips",
                        "quantity": 4,
                        "selected_product_oid": "p_chips",
                        "selected_product_name": "\u6a02\u4e8b\u85af\u7247",
                        "package_quantity": "1\u5305",
                        "unit_price_mop": 4.2,
                        "subtotal_mop": 16.8,
                    }
                ],
                "missing_items": [],
            }
        ],
        "best_plan": {
            "supermarket_oid": "s001",
            "supermarket_name": "\u4f86\u4f86\u8d85\u5e02",
            "point_code": "p001",
            "store_count": 1,
            "estimated_total_mop": 33.8,
            "items": [
                {
                    "raw_item_name": "\u85af\u7247",
                    "intent_id": "chips",
                    "quantity": 4,
                    "selected_product_oid": "p_chips",
                    "selected_product_name": "\u6a02\u4e8b\u85af\u7247",
                    "package_quantity": "1\u5305",
                    "unit_price_mop": 4.2,
                    "subtotal_mop": 16.8,
                }
            ],
            "missing_items": [],
        },
        "warnings": [],
        "diagnostics": {"plan_count": 1},
    }


def test_agent_without_clarification_keeps_ambiguous_items(monkeypatch):
    monkeypatch.setattr("services.shopping_agent_orchestrator.load_products_from_sqlite", lambda db_path: FAKE_PRODUCTS)
    result = run_shopping_agent(QUERY, Path("missing.sqlite3"))

    assert result["status"] == "needs_clarification"
    assert {item["raw_item_name"] for item in result["ambiguous_items"]} >= {"\u9eb5", "\u6cb9", "\u7cd6"}
    assert {item["raw_item_name"] for item in result["resolved_items"]} == {"\u85af\u7247"}


def test_agent_with_clarification_answers_resolves_items_and_builds_price_plan(monkeypatch):
    monkeypatch.setattr("services.shopping_agent_orchestrator.load_products_from_sqlite", lambda db_path: FAKE_PRODUCTS)
    monkeypatch.setattr("services.shopping_agent_price_adapter.plan_cheapest_by_product_candidates", _fake_planner)

    result = run_shopping_agent(
        QUERY,
        Path("missing.sqlite3"),
        point_code="p001",
        include_price_plan=True,
        clarification_answers={
            "\u9eb5": "instant_noodle",
            "\u6cb9": "cooking_oil",
            "\u7cd6": "cooking_sugar",
        },
    )

    assert {item["raw_item_name"] for item in result["ambiguous_items"]} == set()
    resolved = {item["raw_item_name"]: item for item in result["resolved_items"]}
    assert resolved["\u9eb5"]["intent_id"] == "instant_noodle"
    assert resolved["\u6cb9"]["intent_id"] == "cooking_oil"
    assert resolved["\u7cd6"]["intent_id"] == "cooking_sugar"
    assert {item["raw_item_name"] for item in result["not_covered_items"]} >= {"\u85af\u689d", "M&M"}
    assert result["price_plan"]["status"] in {"ok", "partial", "not_priceable"}
    assert "price_plan" in result


def test_agent_invalid_clarification_answer_falls_back_without_crash(monkeypatch):
    monkeypatch.setattr("services.shopping_agent_orchestrator.load_products_from_sqlite", lambda db_path: FAKE_PRODUCTS)

    result = run_shopping_agent(
        QUERY,
        Path("missing.sqlite3"),
        clarification_answers={"\u7cd6": "invalid_intent"},
    )

    assert result["status"] == "needs_clarification"
    assert any("Invalid clarification answer for \u7cd6" in warning for warning in result["warnings"])
    assert {item["raw_item_name"] for item in result["ambiguous_items"]} >= {"\u9eb5", "\u6cb9", "\u7cd6"}
