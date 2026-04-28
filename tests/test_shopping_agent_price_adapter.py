from pathlib import Path

from services.shopping_agent_price_adapter import build_agent_price_plan


def test_build_agent_price_plan_empty_resolved_items():
    result = build_agent_price_plan({"resolved_items": []}, Path("missing.sqlite3"), point_code="p001")
    assert result["status"] == "not_priceable"
    assert result["store_plans"] == []
    assert result["best_plan"] is None


def test_build_agent_price_plan_preserves_non_price_items(monkeypatch):
    agent_result = {
        "resolved_items": [{"raw_item_name": "薯片", "intent_id": "chips", "quantity": 4}],
        "candidate_summary": [{"raw_item_name": "薯片", "top_candidates": [{"product_oid": "p1", "product_name": "樂事薯片", "category_id": 11}]}],
        "ambiguous_items": [{"raw_item_name": "糖"}],
        "not_covered_items": [{"raw_item_name": "M&M"}],
    }
    monkeypatch.setattr(
        "services.shopping_agent_price_adapter.plan_cheapest_by_product_candidates",
        lambda *args, **kwargs: {"status": "ok", "store_plans": [{"estimated_total_mop": 10}], "best_plan": {"estimated_total_mop": 10}, "warnings": [], "diagnostics": {"plan_count": 1}},
    )
    result = build_agent_price_plan(agent_result, Path("missing.sqlite3"), point_code="p001")
    assert result["status"] == "needs_clarification"
    assert result["ambiguous_items"] == [{"raw_item_name": "糖"}]
    assert result["not_covered_items"] == [{"raw_item_name": "M&M"}]
    assert result["priceable_items"][0]["candidate_products"][0]["product_oid"] == "p1"
