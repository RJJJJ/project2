from services.agent_response_composer import compose_agent_response


def test_gemini_composer_fallback_has_safety_diagnostics(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    result = {
        "status": "ok",
        "query_router": {"query_type": "category_search"},
        "resolved_items": [{"raw_item_name": "砂糖"}],
        "price_plan": {"best_plan": {"supermarket_name": "來來超市", "estimated_total_mop": 12.3}},
    }
    message, diagnostics = compose_agent_response(result, composer_mode="gemini")
    assert "MOP 12.30" in message
    assert diagnostics["composer_used"] == "template_fallback"
    assert diagnostics["composer_fallback_reason"]
    assert diagnostics["composer_model"]
