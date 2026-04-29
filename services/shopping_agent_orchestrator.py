from __future__ import annotations

from pathlib import Path
from typing import Any

from services.product_candidate_retriever import retrieve_candidates_by_intent
from services.product_catalog_loader import load_products_from_sqlite
from services.product_intent_resolver import normalize_query_text, resolve_product_intent
from services.product_intent_taxonomy import PRODUCT_INTENTS
from services.simple_basket_parser import parse_simple_basket_text


_RESOLVER_PHRASES = [
    '\u6731\u53e4\u529b\u98f2\u54c1',
    '\u6fd5\u7d19\u5dfe',
    '\u6d17\u982d\u6c34',
    '\u7259\u818f',
    '\u85af\u7247',
    '\u716e\u98df\u7528\u7cd6',
    '\u716e\u98df\u7528\u6cb9',
    '\u98df\u6cb9',
    '\u6d17\u8863\u6db2',
    '\u6d17\u8863\u7c89',
    '\u6d17\u8863\u7682',
]


def _resolver_name(item: dict[str, Any]) -> str:
    keyword = str(item.get("keyword") or "").strip()
    raw_text = str(item.get("raw_text") or "").strip()
    for phrase in _RESOLVER_PHRASES:
        if phrase in raw_text:
            return phrase
    return keyword or raw_text


def _candidate_summary(raw_name: str, intent_id: str, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "raw_item_name": raw_name,
        "intent_id": intent_id,
        "intent_display_name_zh": PRODUCT_INTENTS.get(intent_id, {}).get("display_name_zh", intent_id),
        "candidates_count": len(candidates),
        "top_candidates": candidates[:5],
    }


def _clarification_options(intent_options: list[str]) -> list[dict[str, str]]:
    options: list[dict[str, str]] = []
    for intent_id in intent_options:
        options.append(
            {
                "intent_id": intent_id,
                "label_zh": str(PRODUCT_INTENTS.get(intent_id, {}).get("display_name_zh") or intent_id),
            }
        )
    return options


def _status(
    resolved_items: list[dict[str, Any]],
    ambiguous_items: list[dict[str, Any]],
    not_covered_items: list[dict[str, Any]],
    unknown_items: list[dict[str, Any]],
    price_plan: dict[str, Any] | None = None,
) -> str:
    if ambiguous_items:
        return "needs_clarification"
    if price_plan:
        price_status = price_plan.get("status")
        if resolved_items and price_status == "ok" and not not_covered_items and not unknown_items:
            return "ok"
        if resolved_items and price_status in {"ok", "partial", "needs_clarification"} and (not_covered_items or unknown_items):
            return "partial"
        if not resolved_items and not_covered_items:
            return "not_covered"
    if resolved_items and (not_covered_items or unknown_items):
        return "partial"
    if not resolved_items and not_covered_items and not ambiguous_items and not unknown_items:
        return "not_covered"
    if resolved_items and not ambiguous_items and not not_covered_items and not unknown_items:
        return "ok"
    if unknown_items:
        return "needs_clarification"
    return "error"


def _message(
    status: str,
    resolved_items: list[dict[str, Any]],
    ambiguous_items: list[dict[str, Any]],
    not_covered_items: list[dict[str, Any]],
    unknown_items: list[dict[str, Any]],
) -> str:
    parts: list[str] = []
    if resolved_items:
        labels = '\u3001'.join(f"{item['raw_item_name']} \u2192 {item['intent_display_name_zh']}" for item in resolved_items)
        parts.append(f"\u5df2\u7406\u89e3\u5546\u54c1\uff1a{labels}\u3002")
    if ambiguous_items:
        labels = '\u3001'.join(item["raw_item_name"] for item in ambiguous_items)
        parts.append(f"\u4ee5\u4e0b\u5546\u54c1\u9700\u8981\u4f60\u78ba\u8a8d\u985e\u578b\uff1a{labels}\u3002")
    if not_covered_items:
        labels = '\u3001'.join(item["raw_item_name"] for item in not_covered_items)
        parts.append(f"\u4ee5\u4e0b\u5546\u54c1\u66ab\u672a\u6536\u9304\u516c\u958b\u53ef\u6bd4\u8f03\u50f9\u683c\uff1a{labels}\u3002")
    if unknown_items:
        labels = '\u3001'.join(item["raw_item_name"] for item in unknown_items)
        parts.append(f"\u4ee5\u4e0b\u5546\u54c1\u66ab\u6642\u672a\u80fd\u8b58\u5225\uff1a{labels}\u3002")
    if not parts:
        parts.append("\u66ab\u6642\u672a\u80fd\u5b8c\u6210\u5546\u54c1\u5206\u6790\uff0c\u8acb\u5617\u8a66\u6539\u7528\u66f4\u5e38\u898b\u7684\u5546\u54c1\u540d\u7a31\u3002")
    if status == "needs_clarification":
        parts.append("\u5b8c\u6210\u6f84\u6e05\u5f8c\u53ef\u91cd\u65b0\u8a08\u7b97\u66f4\u5b8c\u6574\u7684\u50f9\u683c\u65b9\u6848\u3002")
    return "".join(parts)


def _normalized_clarification_answers(clarification_answers: dict[str, str] | None) -> dict[str, str]:
    answers: dict[str, str] = {}
    for raw_name, intent_id in (clarification_answers or {}).items():
        normalized_name = normalize_query_text(raw_name)
        normalized_intent = str(intent_id or "").strip()
        if normalized_name:
            answers[normalized_name] = normalized_intent
    return answers


def _user_clarification_resolution(raw_name: str, normalized_name: str, intent_id: str) -> dict[str, Any]:
    display_name = str(PRODUCT_INTENTS.get(intent_id, {}).get("display_name_zh") or intent_id)
    return {
        "raw_item_name": raw_name,
        "normalized_item_name": normalized_name,
        "status": "covered",
        "intent_id": intent_id,
        "intent_options": [],
        "reason": "user_clarification",
        "message_zh": f"\u5df2\u6309\u4f60\u7684\u9078\u64c7\uff0c\u5c07\u300c{raw_name}\u300d\u8996\u70ba\u300c{display_name}\u300d\u3002",
    }


def run_shopping_agent(
    query: str,
    db_path: str | Path,
    point_code: str | None = None,
    use_llm: bool = False,
    debug: bool = False,
    include_price_plan: bool = False,
    price_strategy: str = "cheapest_single_store",
    max_candidates_per_item: int = 5,
    clarification_answers: dict[str, str] | None = None,
) -> dict[str, Any]:
    try:
        parsed_items = parse_simple_basket_text(query)
        products = load_products_from_sqlite(db_path)
        normalized_answers = _normalized_clarification_answers(clarification_answers)

        resolved_items: list[dict[str, Any]] = []
        ambiguous_items: list[dict[str, Any]] = []
        not_covered_items: list[dict[str, Any]] = []
        unknown_items: list[dict[str, Any]] = []
        candidate_summary: list[dict[str, Any]] = []
        warnings: list[str] = []

        for item in parsed_items:
            raw_name = _resolver_name(item)
            normalized_name = normalize_query_text(raw_name)
            clarification_intent = normalized_answers.get(normalized_name)

            if clarification_intent:
                if clarification_intent in PRODUCT_INTENTS:
                    resolution = _user_clarification_resolution(raw_name, normalized_name, clarification_intent)
                else:
                    warnings.append(f"Invalid clarification answer for {raw_name}: {clarification_intent}")
                    resolution = resolve_product_intent(raw_name)
            else:
                resolution = resolve_product_intent(raw_name)

            enriched = {
                "raw_item_name": raw_name,
                "quantity": item.get("quantity", 1),
                "unit": item.get("unit"),
                "resolution": resolution,
            }

            if resolution["status"] == "covered" and resolution.get("intent_id"):
                intent_id = str(resolution["intent_id"])
                candidates = retrieve_candidates_by_intent(products, intent_id, limit=20)
                display = PRODUCT_INTENTS.get(intent_id, {}).get("display_name_zh", intent_id)
                resolved_items.append(
                    {
                        "raw_item_name": raw_name,
                        "quantity": item.get("quantity", 1),
                        "intent_id": intent_id,
                        "intent_display_name_zh": display,
                        "candidates_count": len(candidates),
                        "resolution_reason": resolution.get("reason"),
                    }
                )
                candidate_summary.append(_candidate_summary(raw_name, intent_id, candidates))
            elif resolution["status"] == "ambiguous":
                ambiguous_items.append(
                    enriched
                    | {
                        "message_zh": resolution.get("message_zh"),
                        "clarification_options": _clarification_options(list(resolution.get("intent_options") or [])),
                    }
                )
            elif resolution["status"] == "not_covered":
                not_covered_items.append(enriched | {"message_zh": resolution.get("message_zh")})
            else:
                unknown_items.append(enriched | {"message_zh": resolution.get("message_zh"), "risky": True})

        price_plan = None
        status = _status(resolved_items, ambiguous_items, not_covered_items, unknown_items)
        result = {
            "query": query,
            "point_code": point_code,
            "use_llm": use_llm,
            "status": status,
            "resolved_items": resolved_items,
            "ambiguous_items": ambiguous_items,
            "not_covered_items": not_covered_items,
            "unknown_items": unknown_items,
            "candidate_summary": candidate_summary,
            "warnings": warnings,
            "user_message_zh": _message(status, resolved_items, ambiguous_items, not_covered_items, unknown_items),
            "diagnostics": {
                "products_loaded": len(products),
                "items_parsed": len(parsed_items),
                "resolved_count": len(resolved_items),
                "ambiguous_count": len(ambiguous_items),
                "not_covered_count": len(not_covered_items),
                "unknown_count": len(unknown_items),
                "llm_planner_enabled": bool(use_llm),
                "debug": bool(debug),
                "clarification_answers_count": len(normalized_answers),
            },
        }
        if include_price_plan:
            from services.shopping_agent_price_adapter import build_agent_price_plan

            price_plan = build_agent_price_plan(
                result,
                db_path,
                point_code=point_code,
                strategy=price_strategy,
                max_candidates_per_item=max_candidates_per_item,
            )
            result["price_plan"] = price_plan
            result["status"] = _status(resolved_items, ambiguous_items, not_covered_items, unknown_items, price_plan)
            result["diagnostics"]["price_plan_status"] = price_plan.get("status")
        return result
    except Exception as exc:  # pragma: no cover - defensive API boundary
        return {
            "query": query,
            "point_code": point_code,
            "use_llm": use_llm,
            "status": "error",
            "resolved_items": [],
            "ambiguous_items": [],
            "not_covered_items": [],
            "unknown_items": [],
            "candidate_summary": [],
            "warnings": [],
            "user_message_zh": "\u5206\u6790\u8cfc\u7269\u6e05\u55ae\u6642\u767c\u751f\u932f\u8aa4\uff0c\u8acb\u7a0d\u5f8c\u518d\u8a66\u3002",
            "diagnostics": {"error": str(exc)},
        }
