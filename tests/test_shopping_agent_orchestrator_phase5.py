from services.shopping_agent_orchestrator import run_shopping_agent
from services.sqlite_store import DEFAULT_DB_PATH


def _run(query: str) -> dict:
    return run_shopping_agent(query, DEFAULT_DB_PATH, point_code="p001", include_price_plan=True, debug=True)


def _candidate_text(result: dict) -> str:
    return str(result.get("candidate_summary") or "")


def test_agent_brand_search_integration():
    result = _run("出前一丁")
    assert result["query_router"]["query_type"] == "brand_search"
    assert result["status"] != "not_covered"
    assert "出前一丁" in _candidate_text(result)
    assert "沒有指定口味" in result["user_message_zh"]


def test_agent_partial_product_search_integration():
    result = _run("出前一丁麻油味")
    assert result["query_router"]["query_type"] in {"partial_product_search", "direct_product_search"}
    assert result["resolved_items"]
    assert result["candidate_summary"][0]["top_candidates"][0]["product_name"] == "出前一丁麻油味即食麵(袋裝)"


def test_agent_direct_product_search_integration():
    result = _run("麥老大雞蛋幼面")
    assert result["query_router"]["query_type"] == "direct_product_search"
    assert not result["not_covered_items"]
    assert result["candidate_summary"][0]["top_candidates"][0]["product_name"] == "麥老大雞蛋幼面"


def test_agent_egg_stays_not_covered():
    result = _run("雞蛋")
    assert result["query_router"]["query_type"] == "not_covered_request"
    assert result["status"] == "not_covered"
    assert "麥老大雞蛋幼面" not in _candidate_text(result)


def test_agent_subjective_does_not_fake_taste():
    result = _run("最好吃的麵")
    assert result["query_router"]["query_type"] == "subjective_recommendation"
    assert result["status"] == "unsupported"
    assert "沒有口味" in result["user_message_zh"]
    assert not result.get("price_plan")
