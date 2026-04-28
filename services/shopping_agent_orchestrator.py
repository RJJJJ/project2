from __future__ import annotations

from pathlib import Path
from typing import Any

from services.product_catalog_loader import load_products_from_sqlite
from services.product_candidate_retriever import retrieve_candidates_by_intent
from services.product_intent_resolver import resolve_product_intent
from services.product_intent_taxonomy import PRODUCT_INTENTS
from services.simple_basket_parser import parse_simple_basket_text


def _resolver_name(item: dict[str, Any]) -> str:
    keyword = str(item.get("keyword") or "").strip()
    raw_text = str(item.get("raw_text") or "").strip()
    for phrase in ["朱古力飲品", "濕紙巾", "白砂糖", "砂糖", "煮食油", "食油", "洗髮乳", "洗髮露", "洗髮水"]:
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


def _status(
    resolved_items: list[dict[str, Any]],
    ambiguous_items: list[dict[str, Any]],
    not_covered_items: list[dict[str, Any]],
    unknown_items: list[dict[str, Any]],
) -> str:
    if ambiguous_items:
        return "needs_clarification"
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
        labels = "、".join(f"{item['raw_item_name']}→{item['intent_display_name_zh']}" for item in resolved_items)
        parts.append(f"已理解：{labels}。")
    if ambiguous_items:
        labels = "、".join(item["raw_item_name"] for item in ambiguous_items)
        parts.append(f"需要你再確認：{labels}。")
    if not_covered_items:
        labels = "、".join(item["raw_item_name"] for item in not_covered_items)
        parts.append(f"暫未收錄可比較價格：{labels}。未收錄不代表超市沒有售賣，只代表目前沒有公開監測價格資料。")
    if unknown_items:
        labels = "、".join(item["raw_item_name"] for item in unknown_items)
        parts.append(f"暫時未能判斷商品類型：{labels}。")
    if not parts:
        parts.append("未能識別購物清單，請輸入商品名稱，例如：米、洗頭水、紙巾。")
    if status == "needs_clarification":
        parts.append("請先澄清以上商品類型，再計算最抵買方案。")
    return "".join(parts)


def run_shopping_agent(
    query: str,
    db_path: str | Path,
    point_code: str | None = None,
    use_llm: bool = False,
    debug: bool = False,
) -> dict[str, Any]:
    try:
        parsed_items = parse_simple_basket_text(query)
        products = load_products_from_sqlite(db_path)

        resolved_items: list[dict[str, Any]] = []
        ambiguous_items: list[dict[str, Any]] = []
        not_covered_items: list[dict[str, Any]] = []
        unknown_items: list[dict[str, Any]] = []
        candidate_summary: list[dict[str, Any]] = []

        for item in parsed_items:
            raw_name = _resolver_name(item)
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
                    }
                )
                candidate_summary.append(_candidate_summary(raw_name, intent_id, candidates))
            elif resolution["status"] == "ambiguous":
                ambiguous_items.append(enriched)
            elif resolution["status"] == "not_covered":
                not_covered_items.append(enriched)
            else:
                unknown_items.append(enriched | {"risky": True})

        status = _status(resolved_items, ambiguous_items, not_covered_items, unknown_items)
        return {
            "query": query,
            "point_code": point_code,
            "use_llm": use_llm,
            "status": status,
            "resolved_items": resolved_items,
            "ambiguous_items": ambiguous_items,
            "not_covered_items": not_covered_items,
            "unknown_items": unknown_items,
            "candidate_summary": candidate_summary,
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
            },
        }
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
            "user_message_zh": "系統暫時未能分析這個購物清單，請稍後再試。",
            "diagnostics": {"error": str(exc)},
        }
