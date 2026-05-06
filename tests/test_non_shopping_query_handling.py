from pathlib import Path

from services.shopping_agent_orchestrator import run_shopping_agent


FAKE_PRODUCTS = [
    {"product_oid": "1", "product_name": "\u592a\u53e4\u7d14\u6b63\u7802\u7cd6", "category_id": 5, "category_name": "\u8abf\u5473\u54c1"},
    {"product_oid": "2", "product_name": "\u6ef4\u9732\u6d17\u982d\u6c34\u6ecb\u6f64\u914d\u65b9", "category_id": 6, "category_name": "\u500b\u4eba\u8b77\u7406"},
]


def _run(query: str, monkeypatch, **kwargs):
    monkeypatch.setattr("services.shopping_agent_orchestrator.load_products_from_sqlite", lambda db_path: FAKE_PRODUCTS)
    return run_shopping_agent(query, Path("missing.sqlite3"), include_price_plan=True, **kwargs)


def test_greeting_query_returns_unsupported(monkeypatch):
    result = _run("\u4f60\u597d", monkeypatch, llm_router_enabled=True, llm_router_provider="gemini")
    assert result["status"] == "unsupported"
    assert result["query_router"]["query_type"] == "unsupported_request"
    assert "\u8cfc\u7269\u6e05\u55ae" in result["user_message_zh"] or "\u5546\u54c1\u540d\u7a31" in result["user_message_zh"]
    assert result["resolved_items"] == []
    assert result["price_plan"]["status"] == "not_priceable"
    assert result["diagnostics"]["llm_router_used"] == "skipped"


def test_english_greeting_returns_unsupported(monkeypatch):
    result = _run("hello", monkeypatch, llm_router_enabled=True, llm_router_provider="gemini")
    assert result["status"] == "unsupported"
    assert result["query_router"]["query_type"] == "unsupported_request"


def test_weather_query_returns_unsupported(monkeypatch):
    result = _run("\u4eca\u5929\u5929\u6c23\u5982\u4f55", monkeypatch, llm_router_enabled=True, llm_router_provider="gemini")
    assert result["status"] == "unsupported"
    assert result["query_router"]["query_type"] == "unsupported_request"


def test_normal_basket_query_still_works(monkeypatch):
    result = _run("\u6211\u60f3\u8cb7\u7802\u7cd6\u540c\u6d17\u982d\u6c34", monkeypatch)
    assert result["status"] in {"ok", "partial"}
    assert len(result["resolved_items"]) >= 1


def test_unknown_gibberish_not_marked_as_needs_clarification(monkeypatch):
    result = _run("abcdefgxyz", monkeypatch)
    assert result["status"] in {"unsupported", "unknown", "not_covered", "partial", "ok"}
    assert result["status"] != "needs_clarification"
