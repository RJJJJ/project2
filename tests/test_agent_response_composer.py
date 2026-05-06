from services.agent_response_composer import compose_agent_response, compose_agent_response_template


def _sample_result(status="ok"):
    return {
        "status": status,
        "resolved_items": [{"raw_item_name": "\u7802\u7cd6"}, {"raw_item_name": "\u6d17\u982d\u6c34"}],
        "ambiguous_items": [{"raw_item_name": "\u6cb9"}] if status == "needs_clarification" else [],
        "not_covered_items": [{"raw_item_name": "M&M"}] if status == "partial" else [],
        "price_plan": {"best_plan": {"supermarket_name": "\u4f86\u4f86\u8d85\u5e02", "estimated_total_mop": 44.3}},
    }


def test_template_composer_always_works():
    message = compose_agent_response_template(_sample_result("ok"))
    assert "\u53ef\u6bd4\u8f03\u65b9\u6848" in message
    assert "MOP 44.30" in message


def test_gemini_no_key_falls_back_to_template(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    message, diagnostics = compose_agent_response(_sample_result("needs_clarification"), composer_mode="gemini")
    assert "\u5df2\u78ba\u8a8d\u5546\u54c1" in message
    assert diagnostics["composer_used"] == "template_fallback"
    assert diagnostics["composer_errors"]


def test_template_composer_returns_helpful_unsupported_message():
    message = compose_agent_response_template({"status": "unsupported", "query_router": {"query_type": "unsupported_request"}})
    assert "\u8cfc\u7269\u6e05\u55ae" in message
    assert "\u5546\u54c1\u540d\u7a31" in message
