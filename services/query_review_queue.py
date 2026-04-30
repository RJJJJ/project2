from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _system_action(agent_result: dict[str, Any]) -> str:
    router = agent_result.get("query_router") or {}
    query_type = router.get("query_type")
    status = agent_result.get("status")
    if query_type == "subjective_recommendation" or status == "unsupported":
        return "unsupported"
    if status == "needs_clarification":
        return "clarify"
    if status == "not_covered":
        return "not_covered"
    if any((summary.get("direct_search") or {}).get("status") == "multiple_candidates" for summary in agent_result.get("candidate_summary") or []):
        return "candidate_confirmation"
    return "direct_price"


def build_query_review_record(agent_result: dict) -> dict:
    router = agent_result.get("query_router") or {}
    diagnostics = agent_result.get("diagnostics") or {}
    raw_items = [item.get("raw") for item in router.get("items") or [] if item.get("raw")]
    reasons = list(router.get("reasons") or [])
    needs_review = bool(
        router.get("query_type") == "unknown"
        or router.get("confidence") == "low"
        or agent_result.get("status") in {"needs_clarification", "unsupported", "not_covered"}
        or any((summary.get("direct_search") or {}).get("status") in {"multiple_candidates", "fuzzy_match"} for summary in agent_result.get("candidate_summary") or [])
        or diagnostics.get("clarification_answers_count", 0)
    )
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": agent_result.get("query"),
        "query_type": router.get("query_type", "unknown"),
        "confidence": router.get("confidence", "low"),
        "status": agent_result.get("status"),
        "raw_items": raw_items,
        "system_action": _system_action(agent_result),
        "needs_review": needs_review,
        "reasons": reasons,
        "diagnostics": {
            "router": router,
            "candidate_summary_count": len(agent_result.get("candidate_summary") or []),
            "clarification_answers_count": diagnostics.get("clarification_answers_count", 0),
        },
    }


def append_query_review_record(record: dict, output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
