from services.shopping_decision_policy import build_decision_result, compare_store_plans, summarize_decision_result


def _plan(name, total, store_count=1):
    if store_count == 1:
        return {"supermarket_oid": name, "supermarket_name": name, "store_count": 1, "estimated_total_mop": total, "items": []}
    return {"supermarket_oids": name.split("+"), "supermarket_names": name.split("+"), "store_count": store_count, "estimated_total_mop": total, "items": []}


def test_cheapest_single_store_policy_preserves_best_plan():
    best = _plan("s1", 20)
    result = build_decision_result({"status": "ok", "store_plans": [best], "best_plan": best}, "cheapest_single_store")
    assert result["best_recommendation"] == best
    assert result["policy"] == "cheapest_single_store"


def test_cheapest_two_stores_selects_two_store_when_lower():
    result = compare_store_plans([_plan("s1", 25), _plan("s1+s2", 18, 2)], "cheapest_two_stores")
    assert result["best_recommendation"]["store_count"] == 2
    assert result["best_recommendation"]["estimated_total_mop"] == 18


def test_cheapest_two_stores_keeps_one_store_when_already_best():
    result = compare_store_plans([_plan("s1", 15), _plan("s1+s2", 18, 2)], "cheapest_two_stores")
    assert result["best_recommendation"]["store_count"] == 1


def test_single_store_preferred_threshold_keeps_single_store():
    result = compare_store_plans([_plan("s1", 20), _plan("s1+s2", 17, 2)], "single_store_preferred", {"single_store_threshold_mop": 5})
    assert result["best_recommendation"]["store_count"] == 1


def test_single_store_preferred_threshold_selects_two_store():
    result = compare_store_plans([_plan("s1", 25), _plan("s1+s2", 17, 2)], "single_store_preferred", {"single_store_threshold_mop": 5})
    assert result["best_recommendation"]["store_count"] == 2


def test_balanced_penalty_can_make_single_store_win():
    result = compare_store_plans([_plan("s1", 20), _plan("s1+s2", 17, 2)], "balanced", {"extra_store_penalty_mop": 5})
    assert result["best_recommendation"]["store_count"] == 1
    assert result["diagnostics"]["decision_score"] == 20


def test_build_decision_result_handles_missing_price_plan_safely():
    result = build_decision_result({}, "balanced")
    assert result["status"] == "not_priceable"
    assert result["best_recommendation"] is None
    assert summarize_decision_result(result)
