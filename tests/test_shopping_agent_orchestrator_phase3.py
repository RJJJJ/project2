from pathlib import Path

from services.shopping_agent_orchestrator import run_shopping_agent


FAKE_PRODUCTS = [
    {"product_oid": "p_instant_noodle", "product_name": "\u516c\u4ed4\u9eb5", "category_id": 2, "category_name": "\u9eb5", "package_quantity": "1\u5305"},
    {"product_oid": "p_cooking_oil", "product_name": "\u91d1\u9f8d\u9b5a\u82b1\u751f\u6cb9", "category_id": 3, "category_name": "\u98df\u6cb9", "package_quantity": "1L"},
    {"product_oid": "p_cooking_sugar", "product_name": "\u592a\u53e4\u7d14\u6b63\u7802\u7cd6", "category_id": 5, "category_name": "\u7cd6", "package_quantity": "1kg"},
    {"product_oid": "p_chips", "product_name": "\u6a02\u4e8b\u85af\u7247", "category_id": 11, "category_name": "\u96f6\u98df", "package_quantity": "1\u5305"},
    {"product_oid": "p_shampoo", "product_name": "\u6f58\u5a77\u6d17\u9aee\u9732", "category_id": 10, "category_name": "\u500b\u4eba\u8b77\u7406", "package_quantity": "500ml"},
]


QUERY = "\u5169\u5305\u9eb5 \u4e00\u5305\u85af\u689d \u56db\u5305\u85af\u7247 \u6cb9 \u7cd6 M&M"


def _fake_price_plan(*args, **kwargs):
    return {
        "status": "partial",
        "store_plans": [],
        "best_plan": {
            "supermarket_oid": "s001",
            "supermarket_name": "\u4f86\u4f86\u8d85\u5e02",
            "point_code": "p001",
            "store_count": 1,
            "estimated_total_mop": 33.8,
            "items": [],
            "missing_items": [],
        },
        "warnings": [],
        "diagnostics": {"plan_count": 1},
    }


def test_planner_mode_rule_keeps_existing_behavior(monkeypatch):
    monkeypatch.setattr("services.shopping_agent_orchestrator.load_products_from_sqlite", lambda db_path: FAKE_PRODUCTS)
    result = run_shopping_agent(QUERY, Path("missing.sqlite3"), planner_mode="rule")
    assert result["diagnostics"]["planner_used"] == "rule"
    assert {item["raw_item_name"] for item in result["ambiguous_items"]} >= {"\u9eb5", "\u6cb9", "\u7cd6"}
    assert {item["raw_item_name"] for item in result["not_covered_items"]} >= {"\u85af\u689d", "M&M"}


def test_planner_mode_local_llm_falls_back_without_crash(monkeypatch):
    monkeypatch.setattr("services.shopping_agent_orchestrator.load_products_from_sqlite", lambda db_path: FAKE_PRODUCTS)
    monkeypatch.setattr(
        "services.shopping_agent_orchestrator.plan_query_with_local_llm",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("ollama unavailable")),
    )
    result = run_shopping_agent(
        "\u4eca\u665a\u6253\u908a\u7210\uff0c\u60f3\u8cb7\u5e7e\u652f\u98f2\u54c1\u3001\u7d19\u5dfe\u540c\u4e00\u5305\u7c73\uff0c\u6700\u597d\u5e73\u5572",
        Path("missing.sqlite3"),
        planner_mode="local_llm",
    )
    assert result["status"] in {"needs_clarification", "partial", "ok", "not_covered"}
    assert result["diagnostics"]["planner_used"] == "rule_fallback"
    assert result["diagnostics"]["planner_errors"]


def test_planner_mode_local_llm_uses_mocked_json(monkeypatch):
    monkeypatch.setattr("services.shopping_agent_orchestrator.load_products_from_sqlite", lambda db_path: FAKE_PRODUCTS)
    monkeypatch.setattr(
        "services.shopping_agent_orchestrator.plan_query_with_local_llm",
        lambda *args, **kwargs: {
            "task_type": "basket_price_optimization",
            "language": "zh-HK",
            "items": [
                {"raw": "\u7802\u7cd6", "quantity": 1, "unit": None, "notes": None},
                {"raw": "\u6d17\u982d\u6c34", "quantity": 1, "unit": None, "notes": None},
            ],
            "optimization_goal": "cheapest",
            "location_hint": None,
            "confidence": "high",
            "warnings": [],
        },
    )
    result = run_shopping_agent("\u6211\u60f3\u8cb7\u7802\u7cd6\u540c\u6d17\u982d\u6c34", Path("missing.sqlite3"), planner_mode="local_llm")
    assert result["diagnostics"]["planner_used"] == "local_llm"
    assert {item["intent_id"] for item in result["resolved_items"]} == {"cooking_sugar", "shampoo"}


def test_retrieval_mode_rag_assisted_does_not_crash(monkeypatch):
    monkeypatch.setattr("services.shopping_agent_orchestrator.load_products_from_sqlite", lambda db_path: FAKE_PRODUCTS)
    monkeypatch.setattr("services.shopping_agent_price_adapter.plan_cheapest_by_product_candidates", _fake_price_plan)
    result = run_shopping_agent(
        "\u6211\u60f3\u8cb7\u6d17\u982d\u6c34\u540c\u7802\u7cd6",
        Path("missing.sqlite3"),
        include_price_plan=True,
        retrieval_mode="rag_assisted",
    )
    assert result["diagnostics"]["retrieval_mode"] == "rag_assisted"
    assert result["status"] in {"ok", "partial"}
    assert result["price_plan"]["status"] in {"partial", "not_priceable"}


def test_composer_mode_gemini_without_key_falls_back(monkeypatch):
    monkeypatch.setattr("services.shopping_agent_orchestrator.load_products_from_sqlite", lambda db_path: FAKE_PRODUCTS)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    result = run_shopping_agent("\u6211\u60f3\u8cb7\u7802\u7cd6\u540c\u6d17\u982d\u6c34", Path("missing.sqlite3"), composer_mode="gemini")
    assert result["user_message_zh"]
    assert result["composer_diagnostics"]["composer_used"] == "template_fallback"
