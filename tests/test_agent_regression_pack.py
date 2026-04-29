from scripts.run_agent_regression_pack import build_cases, evaluate_case


def test_regression_pack_case_evaluator_passes_expected_summary():
    case = build_cases(include_rag_cases=False)[0]
    result = {"status": "needs_clarification", "ambiguous_items": [{"raw_item_name": "\u7cd6"}], "not_covered_items": [], "resolved_items": [], "candidate_summary": [], "price_plan": {}}
    passed, failures, summary = evaluate_case(case, result)
    assert passed
    assert failures == []
    assert summary["ambiguous"] == ["\u7cd6"]
