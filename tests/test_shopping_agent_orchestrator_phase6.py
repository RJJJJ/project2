from pathlib import Path

from services.shopping_agent_orchestrator import run_shopping_agent


DB = Path("data/app_state/project2_dev.sqlite3")


def test_orchestrator_rag_v2_direct_flavor_search():
    result = run_shopping_agent("出前一丁麻油味", DB, point_code="p001", include_price_plan=True, retrieval_mode="rag_v2")
    assert result["status"] == "ok"
    assert result["query_router"]["query_type"] in {"partial_product_search", "direct_product_search"}
    top = result["candidate_summary"][0]["top_candidates"][0]
    assert "麻油味" in top["product_name"]
    assert "九州濃湯豬骨" not in top["product_name"]


def test_orchestrator_llm_router_enabled_falls_back_without_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    result = run_shopping_agent("BB用嘅濕紙巾", DB, point_code="p001", include_price_plan=True, retrieval_mode="rag_v2", llm_router_enabled=True)
    assert result["status"] != "error"
    assert result["diagnostics"]["llm_router_used"] == "fallback"


def test_orchestrator_mocked_llm_output_merges(monkeypatch):
    def fake_route(*args, **kwargs):
        return (
            {
                "query": "新品牌",
                "query_type": "brand_search",
                "confidence": "high",
                "items": [{"raw": "新品牌", "quantity": 1, "unit": None, "query_type": "brand_search", "brand": "新品牌", "goal": "unknown"}],
                "needs_clarification": False,
                "clarification_options": [],
                "unsupported_reason": None,
                "reasons": ["mock"],
                "warnings": [],
            },
            {"llm_router_used": "gemini", "llm_router_errors": [], "llm_router_provider": "gemini"},
        )

    monkeypatch.setattr("services.shopping_agent_orchestrator.route_query_with_llm", fake_route)
    result = run_shopping_agent("新品牌", DB, point_code="p001", llm_router_enabled=True)
    assert result["query_router"]["query_type"] == "brand_search"
    assert result["diagnostics"]["router_merge_decision"] in {"llm_accepted", "merged", "rule_kept"}
