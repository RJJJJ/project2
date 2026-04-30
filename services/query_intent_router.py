from __future__ import annotations

import re
from typing import Any

from services.product_direct_search import BRAND_TERMS, HIGH_RISK_SHORT_TERMS, normalize_product_name_for_lookup, should_try_direct_product_search


QUERY_TYPES = {
    "basket_optimization",
    "direct_product_search",
    "partial_product_search",
    "brand_search",
    "category_search",
    "subjective_recommendation",
    "ambiguous_request",
    "not_covered_request",
    "unsupported_request",
    "unknown",
}

SUBJECTIVE_TOKENS = ("最好吃", "最好食", "好吃", "好食", "最健康", "健康", "好用", "推薦")
UNSUPPORTED_TOKENS = ("最多人買", "庫存", "有沒有貨", "有冇貨", "今日特價", "有沒有特價", "評分")
CHEAPEST_TOKENS = ("最平", "平啲", "便宜", "最低價", "cheapest", "抵買")
LIST_TOKENS = ("列出", "有咩", "有什麼", "款式", "選擇")
NOT_COVERED = {"雞蛋", "蛋", "薯條", "M&M", "m&m"}
AMBIGUOUS = {"麵", "面", "油", "糖", "紙巾", "朱古力", "飲品", "米", "奶", "水", "紙"}
CATEGORY_TERMS = {"即食麵", "公仔麵", "砂糖", "洗頭水", "食油", "薯片", "濕紙巾", "牙膏", "豆奶", "朱古力飲品"}


def _goal(query: str) -> str:
    text = str(query or "")
    if any(token in text for token in CHEAPEST_TOKENS):
        return "cheapest"
    if any(token in text for token in LIST_TOKENS):
        return "list_options"
    if "價" in text or "幾錢" in text:
        return "specific_price"
    if any(token in text for token in SUBJECTIVE_TOKENS):
        return "subjective"
    return "unknown"


def _raw_items_from_planner(query: str, planner_output: dict[str, Any] | None) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for item in (planner_output or {}).get("items") or []:
        raw = str(item.get("raw") or "").strip()
        if not raw:
            continue
        items.append({"raw": raw, "quantity": item.get("quantity") or 1, "unit": item.get("unit")})
    if items:
        return items
    query = str(query or "").strip()
    return [{"raw": query, "quantity": 1, "unit": None}] if query else []


def _clean_single_query(query: str) -> str:
    text = str(query or "").strip()
    for prefix in ("我想買", "想買", "幫我格價", "幫我查", "查下", "查"):
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
    for token in ("最便宜的", "最平嘅", "最平的", *CHEAPEST_TOKENS):
        text = text.replace(token, "")
    text = re.sub(r"^[的嘅之]+", "", text)
    return text.strip(" ：:，,。")


def route_item_intent(raw_item_name: str, context: dict | None = None) -> dict:
    raw = str(raw_item_name or "").strip()
    normalized = normalize_product_name_for_lookup(raw)
    goal = _goal(str((context or {}).get("query") or raw))
    reasons: list[str] = []
    brand = next((brand for brand in BRAND_TERMS if normalize_product_name_for_lookup(brand) == normalized or normalize_product_name_for_lookup(brand) in normalized), None)

    query_type = "unknown"
    confidence = "low"
    category_hint = None
    product_clues: list[str] = []
    unsupported_reason = None
    needs_clarification = False
    clarification_options: list[dict[str, Any]] = []

    if raw in NOT_COVERED or normalized in {normalize_product_name_for_lookup(term) for term in NOT_COVERED}:
        query_type = "not_covered_request"
        confidence = "high"
        unsupported_reason = "not covered by current public price catalog"
        reasons.append("explicit not-covered item")
    elif raw in AMBIGUOUS or normalized in {normalize_product_name_for_lookup(term) for term in AMBIGUOUS}:
        query_type = "ambiguous_request"
        confidence = "high"
        needs_clarification = True
        clarification_options = [{"label_zh": label, "intent_id": label} for label in ["請選擇更具體類別或品牌"]]
        reasons.append("high-risk short generic term")
    elif any(token in raw for token in SUBJECTIVE_TOKENS):
        query_type = "subjective_recommendation"
        confidence = "high"
        unsupported_reason = "subjective quality data unavailable"
        reasons.append("subjective preference token detected")
    elif any(token in raw for token in UNSUPPORTED_TOKENS):
        query_type = "unsupported_request"
        confidence = "high"
        unsupported_reason = "requested signal is not in current data source"
        reasons.append("unsupported data token detected")
    elif brand and normalized == normalize_product_name_for_lookup(brand):
        query_type = "brand_search"
        confidence = "high"
        reasons.append("brand-only query")
    elif brand and should_try_direct_product_search(raw):
        query_type = "partial_product_search"
        confidence = "high"
        product_clues = [brand]
        reasons.append("brand plus product/flavor clues")
    elif raw in CATEGORY_TERMS or normalized in {normalize_product_name_for_lookup(term) for term in CATEGORY_TERMS}:
        query_type = "category_search"
        confidence = "high"
        category_hint = raw
        reasons.append("known category term")
    elif should_try_direct_product_search(raw) and len(normalized) >= 5:
        query_type = "direct_product_search"
        confidence = "medium"
        reasons.append("specific product-like query")
    else:
        query_type = "unknown"
        confidence = "low"
        reasons.append("no router rule matched")

    return {
        "raw": raw,
        "quantity": int((context or {}).get("quantity") or 1),
        "unit": (context or {}).get("unit"),
        "query_type": query_type,
        "brand": brand,
        "category_hint": category_hint,
        "product_clues": product_clues,
        "goal": goal,
        "confidence": confidence,
        "needs_clarification": needs_clarification,
        "clarification_options": clarification_options,
        "unsupported_reason": unsupported_reason,
        "reasons": reasons,
    }


def classify_query_type(query: str, raw_items: list[dict] | None = None) -> dict:
    text = str(query or "").strip()
    clean = _clean_single_query(text)
    reasons: list[str] = []
    if any(token in text for token in SUBJECTIVE_TOKENS):
        return {"query_type": "subjective_recommendation", "confidence": "high", "reasons": ["subjective token in query"]}
    if any(token in text for token in UNSUPPORTED_TOKENS):
        return {"query_type": "unsupported_request", "confidence": "high", "reasons": ["unsupported token in query"]}
    items = raw_items or [{"raw": clean or text, "quantity": 1, "unit": None}]
    if len(items) > 1:
        return {"query_type": "basket_optimization", "confidence": "high", "reasons": ["multiple shopping items"]}
    item_decision = route_item_intent(str(items[0].get("raw") or clean or text), {"query": text, **items[0]})
    reasons.extend(item_decision.get("reasons") or [])
    return {"query_type": item_decision["query_type"], "confidence": item_decision["confidence"], "reasons": reasons}


def build_router_decision(query_type: str, confidence: str, raw_items: list[dict], reasons: list[str], clarification_options: list[dict] | None = None) -> dict:
    needs_clarification = query_type == "ambiguous_request" or any(bool(item.get("needs_clarification")) for item in raw_items)
    return {
        "query": "",
        "query_type": query_type if query_type in QUERY_TYPES else "unknown",
        "confidence": confidence if confidence in {"high", "medium", "low"} else "low",
        "items": raw_items,
        "needs_clarification": needs_clarification,
        "clarification_options": clarification_options or [],
        "unsupported_reason": None,
        "reasons": reasons,
        "warnings": [],
    }


def route_user_query(query: str, planner_output: dict | None = None, use_llm_router: bool = False, llm_router_options: dict | None = None) -> dict:
    planner_items = _raw_items_from_planner(query, planner_output)
    clean_query = _clean_single_query(query)
    if len(planner_items) == 1 and clean_query and clean_query != planner_items[0].get("raw") and not re.search(r"[，,、\s]", clean_query):
        planner_items = [{"raw": clean_query, "quantity": planner_items[0].get("quantity") or 1, "unit": planner_items[0].get("unit")}]

    routed_items = [route_item_intent(str(item.get("raw") or ""), {"query": query, **item}) for item in planner_items]
    classification = classify_query_type(query, routed_items)
    query_type = classification["query_type"]
    confidence = classification["confidence"]
    reasons = [*classification.get("reasons", [])]
    for item in routed_items:
        reasons.extend(item.get("reasons") or [])
    unsupported = next((item.get("unsupported_reason") for item in routed_items if item.get("unsupported_reason")), None)
    decision = build_router_decision(query_type, confidence, routed_items, list(dict.fromkeys(reasons)))
    decision.update(
        {
            "query": query,
            "unsupported_reason": unsupported,
            "clarification_options": [option for item in routed_items for option in (item.get("clarification_options") or [])],
            "warnings": ["llm router requested but not enabled in MVP"] if use_llm_router else [],
        }
    )
    return decision
