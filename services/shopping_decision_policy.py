from __future__ import annotations

from typing import Any

SUPPORTED_POLICIES = {"cheapest_single_store", "cheapest_two_stores", "single_store_preferred", "balanced"}


def _money(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def _store_count(plan: dict[str, Any] | None) -> int | None:
    if not plan:
        return None
    try:
        return max(1, int(plan.get("store_count") or 1))
    except (TypeError, ValueError):
        return 1


def _plan_sort_key(plan: dict[str, Any]) -> tuple[Any, ...]:
    return (
        _money(plan.get("estimated_total_mop")) if _money(plan.get("estimated_total_mop")) is not None else float("inf"),
        _store_count(plan) or 99,
        ",".join(str(x) for x in plan.get("supermarket_names") or [plan.get("supermarket_name") or ""]),
        ",".join(str(x) for x in plan.get("supermarket_oids") or [plan.get("supermarket_oid") or ""]),
    )


def _with_score(plan: dict[str, Any] | None, score: float | None) -> dict[str, Any] | None:
    if not plan:
        return None
    copied = dict(plan)
    if score is not None:
        copied["decision_score"] = round(float(score), 2)
    return copied


def _explanation(policy: str, recommendation: dict[str, Any] | None, status: str) -> str:
    if status in {"needs_clarification", "partial"}:
        prefix = "???????????????????????????????????????"
    elif status == "not_priceable":
        return "????????????????????????"
    elif status == "error":
        return "??????????????????"
    else:
        prefix = ""
    policy_text = {
        "cheapest_single_store": "???????????????",
        "cheapest_two_stores": "????????????????????????????????",
        "single_store_preferred": "????????????????????????????????????",
        "balanced": "???????????????",
    }.get(policy, "??????????????????")
    if not recommendation:
        return (prefix + policy_text).strip()
    total = _money(recommendation.get("estimated_total_mop"))
    count = _store_count(recommendation)
    suffix = "" if total is None else f" ???????? MOP {total:.2f}???? {count or 1} ???"
    return (prefix + policy_text + suffix).strip()


def compare_store_plans(store_plans: list[dict[str, Any]], policy: str, policy_options: dict | None = None) -> dict[str, Any]:
    options = dict(policy_options or {})
    normalized_policy = policy if policy in SUPPORTED_POLICIES else "cheapest_single_store"
    plans = [dict(plan) for plan in (store_plans or []) if isinstance(plan, dict)]
    single_plans = sorted([p for p in plans if _store_count(p) == 1], key=_plan_sort_key)
    two_plans = sorted([p for p in plans if (_store_count(p) or 1) <= 2], key=_plan_sort_key)
    single_best = single_plans[0] if single_plans else None
    two_best = two_plans[0] if two_plans else None
    warnings: list[str] = []
    thresholds: dict[str, float] = {}

    selected: dict[str, Any] | None = None
    decision_score: float | None = None
    if normalized_policy == "cheapest_single_store":
        selected = single_best
    elif normalized_policy == "cheapest_two_stores":
        selected = two_best or single_best
    elif normalized_policy == "single_store_preferred":
        threshold = float(options.get("single_store_threshold_mop", 5.0))
        thresholds["single_store_threshold_mop"] = threshold
        selected = single_best
        if single_best and two_best:
            single_total = _money(single_best.get("estimated_total_mop"))
            two_total = _money(two_best.get("estimated_total_mop"))
            if single_total is not None and two_total is not None and (single_total - two_total) > threshold:
                selected = two_best
        elif two_best:
            selected = two_best
    elif normalized_policy == "balanced":
        penalty = float(options.get("extra_store_penalty_mop", 5.0))
        thresholds["extra_store_penalty_mop"] = penalty
        scored: list[tuple[float, dict[str, Any]]] = []
        for plan in [p for p in plans if (_store_count(p) or 1) <= 2]:
            total = _money(plan.get("estimated_total_mop"))
            if total is None:
                continue
            score = total + ((_store_count(plan) or 1) - 1) * penalty
            scored.append((round(score, 2), plan))
        scored.sort(key=lambda pair: (pair[0], _plan_sort_key(pair[1])))
        if scored:
            decision_score, selected_plan = scored[0]
            selected = _with_score(selected_plan, decision_score)

    alternatives = []
    selected_key = id(selected) if selected is not None else None
    for plan in sorted(plans, key=_plan_sort_key):
        if selected is not None and plan == {k: v for k, v in selected.items() if k != "decision_score"}:
            continue
        alternatives.append(plan)
        if len(alternatives) >= 3:
            break

    if not selected:
        warnings.append("No complete store plan available for this policy.")
    selected_count = _store_count(selected)
    if selected and decision_score is None and selected.get("decision_score") is not None:
        decision_score = _money(selected.get("decision_score"))
    return {
        "policy": normalized_policy,
        "best_recommendation": selected,
        "alternatives": alternatives,
        "single_store_best": single_best,
        "two_store_best": two_best,
        "warnings": warnings,
        "diagnostics": {
            "policy": normalized_policy,
            "single_store_plan_count": len(single_plans),
            "two_store_plan_count": len(two_plans),
            "selected_store_count": selected_count,
            "decision_score": decision_score,
            "thresholds": thresholds,
        },
    }


def build_decision_result(price_plan: dict, policy: str = "cheapest_single_store", policy_options: dict | None = None) -> dict:
    normalized_policy = policy if policy in SUPPORTED_POLICIES else "cheapest_single_store"
    if not isinstance(price_plan, dict) or not price_plan:
        result = compare_store_plans([], normalized_policy, policy_options)
        return result | {"status": "not_priceable", "decision_explanation_zh": _explanation(normalized_policy, None, "not_priceable")}

    status = str(price_plan.get("status") or "not_priceable")
    if status not in {"ok", "partial", "not_priceable", "needs_clarification", "error"}:
        status = "error"
    single_plans = list(price_plan.get("store_plans") or [])
    two_plans = list(price_plan.get("two_store_plans") or [])
    if normalized_policy == "cheapest_single_store":
        plans = single_plans
    else:
        plans = [*single_plans, *two_plans]
    compared = compare_store_plans(plans, normalized_policy, policy_options)
    recommendation = compared.get("best_recommendation")
    if not recommendation and price_plan.get("best_plan") and normalized_policy == "cheapest_single_store":
        recommendation = price_plan.get("best_plan")
        compared["best_recommendation"] = recommendation
    decision_status = status if recommendation else ("needs_clarification" if status == "needs_clarification" else "not_priceable")
    warnings = list(dict.fromkeys([*(price_plan.get("warnings") or []), *(compared.get("warnings") or [])]))
    return {
        "policy": normalized_policy,
        "status": decision_status,
        "best_recommendation": recommendation,
        "alternatives": compared.get("alternatives") or [],
        "single_store_best": compared.get("single_store_best") or price_plan.get("best_plan"),
        "two_store_best": compared.get("two_store_best") or price_plan.get("two_store_best"),
        "decision_explanation_zh": _explanation(normalized_policy, recommendation, decision_status),
        "warnings": warnings,
        "diagnostics": compared.get("diagnostics") or {},
    }


def summarize_decision_result(decision_result: dict) -> str:
    if not isinstance(decision_result, dict) or not decision_result.get("best_recommendation"):
        return "??????????????"
    recommendation = decision_result["best_recommendation"]
    total = _money(recommendation.get("estimated_total_mop"))
    store_count = _store_count(recommendation) or 1
    names = recommendation.get("supermarket_names") or [recommendation.get("supermarket_name")]
    stores = "?".join(str(name) for name in names if name) or "?????"
    total_text = "N/A" if total is None else f"MOP {total:.2f}"
    return f"{decision_result.get('decision_explanation_zh') or ''} ???{stores}????{store_count}??????{total_text}?".strip()
