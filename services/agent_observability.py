from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _len(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def _first_number(*values: Any) -> float | None:
    for value in values:
        try:
            if value is not None:
                return round(float(value), 2)
        except (TypeError, ValueError):
            continue
    return None


def build_agent_observation(agent_result: dict, started_at: float | None = None, ended_at: float | None = None) -> dict:
    result = agent_result if isinstance(agent_result, dict) else {}
    diagnostics = result.get("diagnostics") or {}
    price_plan = result.get("price_plan") or {}
    decision_result = price_plan.get("decision_result") or {}
    recommendation = decision_result.get("best_recommendation") or price_plan.get("best_plan") or {}
    latency_ms = None
    if started_at is not None and ended_at is not None:
        latency_ms = round(max(0.0, float(ended_at) - float(started_at)) * 1000, 2)
    errors = []
    for key in ("error", "planner_errors", "composer_errors"):
        value = diagnostics.get(key)
        if isinstance(value, list):
            errors.extend(str(item) for item in value if item)
        elif value:
            errors.append(str(value))
    warnings = []
    for source in (result.get("warnings"), price_plan.get("warnings"), decision_result.get("warnings")):
        if isinstance(source, list):
            warnings.extend(str(item) for item in source if item)
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": result.get("query"),
        "status": result.get("status"),
        "planner_mode": diagnostics.get("planner_mode"),
        "planner_used": diagnostics.get("planner_used"),
        "retrieval_mode": diagnostics.get("retrieval_mode"),
        "rag_used": bool(diagnostics.get("rag_used")),
        "composer_mode": diagnostics.get("composer_mode"),
        "composer_used": diagnostics.get("composer_used"),
        "decision_policy": decision_result.get("policy") or diagnostics.get("decision_policy") or price_plan.get("strategy"),
        "price_plan_status": price_plan.get("status") or diagnostics.get("price_plan_status"),
        "ambiguous_count": _len(result.get("ambiguous_items")),
        "not_covered_count": _len(result.get("not_covered_items")),
        "unknown_count": _len(result.get("unknown_items")),
        "resolved_count": _len(result.get("resolved_items")),
        "priceable_item_count": _len(price_plan.get("priceable_items")),
        "plan_count": len(price_plan.get("store_plans") or []),
        "best_total_mop": _first_number(recommendation.get("estimated_total_mop"), (price_plan.get("best_plan") or {}).get("estimated_total_mop")),
        "selected_store_count": decision_result.get("diagnostics", {}).get("selected_store_count") or recommendation.get("store_count"),
        "latency_ms": latency_ms,
        "errors": list(dict.fromkeys(errors)),
        "warnings": list(dict.fromkeys(warnings)),
    }


def append_agent_observation_jsonl(observation: dict, output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(observation, ensure_ascii=False, sort_keys=True) + "\n")
