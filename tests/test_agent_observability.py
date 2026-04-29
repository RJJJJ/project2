import json

from services.agent_observability import append_agent_observation_jsonl, build_agent_observation


def test_observation_builds_expected_keys(tmp_path):
    result = {"query": "??", "status": "ok", "resolved_items": [{"raw_item_name": "??"}], "ambiguous_items": [], "not_covered_items": [], "unknown_items": [], "diagnostics": {"planner_mode": "rule", "planner_used": "rule", "retrieval_mode": "taxonomy", "composer_mode": "template", "composer_used": "template"}, "price_plan": {"status": "ok", "priceable_items": [{}], "store_plans": [{}], "decision_result": {"policy": "balanced", "best_recommendation": {"estimated_total_mop": 12, "store_count": 1}, "diagnostics": {"selected_store_count": 1}}}}
    observation = build_agent_observation(result, started_at=1.0, ended_at=1.2)
    for key in ["timestamp", "query", "status", "planner_used", "retrieval_mode", "composer_used", "decision_policy", "price_plan_status", "latency_ms"]:
        assert key in observation
    assert observation["decision_policy"] == "balanced"
    path = tmp_path / "obs.jsonl"
    append_agent_observation_jsonl(observation, path)
    assert json.loads(path.read_text(encoding="utf-8"))["query"] == "??"
