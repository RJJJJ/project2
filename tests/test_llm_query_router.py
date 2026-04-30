from services.llm_query_router import merge_rule_and_llm_router_outputs, validate_llm_router_output


def _payload(query_type="brand_search", confidence="high"):
    return {
        "query": "出前一丁",
        "query_type": query_type,
        "confidence": confidence,
        "items": [
            {
                "raw": "出前一丁",
                "quantity": 1,
                "unit": None,
                "query_type": query_type,
                "brand": "出前一丁",
                "category_hint": None,
                "product_clues": [],
                "goal": "unknown",
                "confidence": confidence,
                "needs_clarification": False,
                "clarification_options": [],
            }
        ],
        "needs_clarification": False,
        "clarification_options": [],
        "unsupported_reason": None,
        "reasons": [],
        "warnings": [],
    }


def test_validate_llm_router_output_accepts_valid_payload():
    ok, errors = validate_llm_router_output(_payload())
    assert ok
    assert errors == []


def test_validate_llm_router_output_rejects_invalid_schema():
    ok, errors = validate_llm_router_output({"query_type": "bad", "confidence": "maybe", "items": {}})
    assert not ok
    assert errors


def test_guarded_merge_keeps_not_covered_egg():
    rule = {"query": "雞蛋", "query_type": "not_covered_request", "confidence": "high", "items": [{"raw": "雞蛋"}]}
    llm = _payload("direct_product_search")
    llm["query"] = "雞蛋"
    merged = merge_rule_and_llm_router_outputs(rule, llm)
    assert merged["query_type"] == "not_covered_request"
    assert merged["diagnostics"]["router_merge_decision"] == "rule_kept"


def test_guarded_merge_keeps_ambiguous_sugar():
    rule = {"query": "糖", "query_type": "ambiguous_request", "confidence": "high", "items": [{"raw": "糖"}]}
    llm = _payload("direct_product_search")
    llm["query"] = "糖"
    merged = merge_rule_and_llm_router_outputs(rule, llm)
    assert merged["query_type"] == "ambiguous_request"


def test_guarded_merge_accepts_high_confidence_when_rule_unknown():
    rule = {"query": "新品牌", "query_type": "unknown", "confidence": "low", "items": [{"raw": "新品牌"}]}
    llm = _payload("brand_search")
    llm["query"] = "新品牌"
    merged = merge_rule_and_llm_router_outputs(rule, llm)
    assert merged["query_type"] == "brand_search"
