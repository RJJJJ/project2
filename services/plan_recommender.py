from __future__ import annotations

from typing import Any


def _plan_by_type(plans: list[dict[str, Any]], plan_type: str) -> dict[str, Any] | None:
    for plan in plans:
        if plan.get("plan_type") == plan_type:
            return plan
    return None


def _total(plan: dict[str, Any] | None) -> float | None:
    if not plan:
        return None
    value = plan.get("estimated_total_mop")
    if value is None:
        return None
    return float(value)


def recommend_plan(
    plans: list[dict[str, Any]],
    convenience_threshold_mop: float = 5.0,
) -> dict[str, str | None]:
    cheapest_by_item = _plan_by_type(plans, "cheapest_by_item")
    cheapest_single_store = _plan_by_type(plans, "cheapest_single_store")
    cheapest_two_stores = _plan_by_type(plans, "cheapest_two_stores")

    by_item_total = _total(cheapest_by_item)
    single_store_total = _total(cheapest_single_store)
    two_stores_total = _total(cheapest_two_stores)

    if single_store_total is not None and by_item_total is not None:
        premium = single_store_total - by_item_total
        if premium <= convenience_threshold_mop:
            return {
                "recommended_plan_type": "cheapest_single_store",
                "recommendation_reason": f"只比最低價方案貴 {premium:.1f} MOP，但只需去一間店。",
            }

    if two_stores_total is not None:
        return {
            "recommended_plan_type": "cheapest_two_stores",
            "recommendation_reason": "在最多兩間店限制下取得最低總價。",
        }

    return {
        "recommended_plan_type": "cheapest_by_item",
        "recommendation_reason": "只能按單品最低價提供參考方案。",
    }
