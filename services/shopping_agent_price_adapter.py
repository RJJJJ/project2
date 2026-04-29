from __future__ import annotations

from pathlib import Path
from typing import Any

from services.product_oid_price_planner import plan_cheapest_by_product_candidates, plan_cheapest_by_product_candidates_two_stores
from services.shopping_decision_policy import build_decision_result


def _candidate_summary_by_raw(agent_result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(summary.get("raw_item_name")): summary
        for summary in agent_result.get("candidate_summary") or []
        if summary.get("raw_item_name")
    }


def _priceable_items(agent_result: dict[str, Any], max_candidates_per_item: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    summaries = _candidate_summary_by_raw(agent_result)
    priceable: list[dict[str, Any]] = []
    unpriceable: list[dict[str, Any]] = []
    for item in agent_result.get("resolved_items") or []:
        raw_name = str(item.get("raw_item_name") or "")
        candidates = list((summaries.get(raw_name) or {}).get("top_candidates") or [])[: max(0, int(max_candidates_per_item))]
        entry = {
            "raw_item_name": raw_name,
            "intent_id": item.get("intent_id"),
            "quantity": item.get("quantity", 1),
            "unit": item.get("unit"),
            "candidate_products": [
                {
                    "product_oid": candidate.get("product_oid"),
                    "product_name": candidate.get("product_name"),
                    "category_id": candidate.get("category_id"),
                    "category_name": candidate.get("category_name"),
                    "package_quantity": candidate.get("package_quantity"),
                }
                for candidate in candidates
                if candidate.get("product_oid") is not None
            ],
        }
        if entry["candidate_products"]:
            priceable.append(entry)
        else:
            unpriceable.append(entry | {"reason": "no_candidate_products"})
    return priceable, unpriceable


def _adapter_status(
    planner_status: str,
    has_priceable: bool,
    has_best_plan: bool,
    ambiguous_items: list[dict[str, Any]],
    not_covered_items: list[dict[str, Any]],
    unpriceable_items: list[dict[str, Any]],
) -> str:
    if not has_priceable:
        return "not_priceable"
    if ambiguous_items:
        return "needs_clarification"
    if has_best_plan and (not_covered_items or unpriceable_items):
        return "partial"
    if has_best_plan and planner_status == "ok":
        return "ok"
    return "not_priceable"


def build_agent_price_plan(
    agent_result: dict[str, Any],
    db_path: str | Path,
    point_code: str | None = None,
    strategy: str = "cheapest_single_store",
    max_candidates_per_item: int = 5,
    decision_policy: str | None = None,
    decision_policy_options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    warnings: list[str] = []
    priceable_items, unpriceable_items = _priceable_items(agent_result, max_candidates_per_item)
    ambiguous_items = list(agent_result.get("ambiguous_items") or [])
    not_covered_items = list(agent_result.get("not_covered_items") or [])

    if not priceable_items:
        return {
            "status": "not_priceable",
            "strategy": strategy,
            "priceable_items": [],
            "unpriceable_items": unpriceable_items,
            "ambiguous_items": ambiguous_items,
            "not_covered_items": not_covered_items,
            "store_plans": [],
            "best_plan": None,
            "warnings": ["No resolved items with candidate products to price."],
            "decision_result": build_decision_result({}, decision_policy or strategy, decision_policy_options),
            "diagnostics": {
                "priceable_item_count": 0,
                "unpriceable_item_count": len(unpriceable_items),
                "ambiguous_count": len(ambiguous_items),
                "not_covered_count": len(not_covered_items),
                "plan_count": 0,
            },
        }

    requested_policy = decision_policy or strategy or "cheapest_single_store"
    single_result = plan_cheapest_by_product_candidates(db_path, point_code, priceable_items, strategy="cheapest_single_store")
    warnings.extend(single_result.get("warnings") or [])
    two_result: dict[str, Any] | None = None
    if requested_policy in {"cheapest_two_stores", "single_store_preferred", "balanced"}:
        two_result = plan_cheapest_by_product_candidates_two_stores(
            db_path,
            point_code,
            priceable_items,
            max_candidates_per_item=max_candidates_per_item,
        )
        warnings.extend(two_result.get("warnings") or [])
    if unpriceable_items:
        warnings.append("Some resolved items have no candidate products and were not priced.")

    best_plan = single_result.get("best_plan")
    status = _adapter_status(
        str(single_result.get("status")),
        bool(priceable_items),
        bool(best_plan or (two_result or {}).get("best_plan")),
        ambiguous_items,
        not_covered_items,
        unpriceable_items,
    )
    base_plan = {
        "status": status,
        "strategy": strategy,
        "priceable_items": priceable_items,
        "unpriceable_items": unpriceable_items,
        "ambiguous_items": ambiguous_items,
        "not_covered_items": not_covered_items,
        "store_plans": single_result.get("store_plans") or [],
        "best_plan": best_plan,
        "two_store_plans": (two_result or {}).get("store_plans") or [],
        "two_store_best": (two_result or {}).get("best_plan"),
        "item_availability": (two_result or {}).get("item_availability") or [],
        "warnings": list(dict.fromkeys(warnings)),
        "diagnostics": {
            **(single_result.get("diagnostics") or {}),
            "priceable_item_count": len(priceable_items),
            "unpriceable_item_count": len(unpriceable_items),
            "ambiguous_count": len(ambiguous_items),
            "not_covered_count": len(not_covered_items),
            "plan_count": len(single_result.get("store_plans") or []),
            "two_store_plan_count": len((two_result or {}).get("store_plans") or []),
            "decision_policy": requested_policy,
        },
    }
    base_plan["decision_result"] = build_decision_result(base_plan, requested_policy, decision_policy_options)
    return base_plan
