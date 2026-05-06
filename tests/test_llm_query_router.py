from services.llm_query_router import merge_rule_and_llm_router_outputs, validate_llm_router_output


def _payload(query_type="brand_search", confidence="high"):
    return {
        "query": "\u51fa\u524d\u4e00\u4e01",
        "query_type": query_type,
        "confidence": confidence,
        "items": [
            {
                "raw": "\u51fa\u524d\u4e00\u4e01",
                "quantity": 1,
                "unit": None,
                "query_type": query_type,
                "brand": "\u51fa\u524d\u4e00\u4e01",
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
    rule = {"query": "\u96de\u86cb", "query_type": "not_covered_request", "confidence": "high", "items": [{"raw": "\u96de\u86cb"}]}
    llm = _payload("direct_product_search")
    llm["query"] = "\u96de\u86cb"
    merged = merge_rule_and_llm_router_outputs(rule, llm)
    assert merged["query_type"] == "not_covered_request"
    assert merged["diagnostics"]["router_merge_decision"] == "rule_kept"


def test_guarded_merge_keeps_ambiguous_sugar():
    rule = {"query": "\u7cd6", "query_type": "ambiguous_request", "confidence": "high", "items": [{"raw": "\u7cd6"}]}
    llm = _payload("direct_product_search")
    llm["query"] = "\u7cd6"
    merged = merge_rule_and_llm_router_outputs(rule, llm)
    assert merged["query_type"] == "ambiguous_request"


def test_guarded_merge_accepts_high_confidence_when_rule_unknown():
    rule = {"query": "\u51fa\u524d\u4e00\u4e01", "query_type": "unknown", "confidence": "low", "items": [{"raw": "\u51fa\u524d\u4e00\u4e01"}]}
    llm = _payload("brand_search")
    llm["query"] = "\u51fa\u524d\u4e00\u4e01"
    merged = merge_rule_and_llm_router_outputs(rule, llm)
    assert merged["query_type"] == "brand_search"


def test_guarded_merge_keeps_high_confidence_unsupported_rule():
    rule = {
        "query": "\u4f60\u597d",
        "query_type": "unsupported_request",
        "confidence": "high",
        "items": [{"raw": "\u4f60\u597d"}],
        "reasons": ["non-shopping/greeting query detected"],
    }
    llm = _payload("brand_search")
    llm["query"] = "\u4f60\u597d"
    merged = merge_rule_and_llm_router_outputs(rule, llm)
    assert merged["query_type"] == "unsupported_request"
    assert merged["diagnostics"]["router_merge_decision"] == "rule_kept"
