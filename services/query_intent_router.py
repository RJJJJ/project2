from __future__ import annotations

import re
from typing import Any

from services.brand_mining import detect_brand_query
from services.product_direct_search import (
    BRAND_TERMS,
    normalize_product_name_for_lookup,
    should_try_direct_product_search,
)

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

SUBJECTIVE_TOKENS = (
    "\u6700\u597d\u5403",
    "\u597d\u5403",
    "\u63a8\u85a6",
    "\u503c\u5f97\u8cb7",
    "\u908a\u96bb\u597d",
    "\u54ea\u500b\u597d",
    "suggest",
)
UNSUPPORTED_TOKENS = (
    "\u5929\u6c23",
    "\u529f\u8ab2",
    "\u8b1b\u7b11\u8a71",
    "\u7b11\u8a71",
    "\u4f5c\u696d",
    "homework",
    "weather",
)
CHEAPEST_TOKENS = ("\u6700\u5e73", "\u6700\u62b5", "\u6700\u4fbf\u5b9c", "cheapest", "\u5e73\u5572")
LIST_TOKENS = ("\u6709\u54a9", "\u6709\u4ec0\u9ebc", "\u6709\u6c92\u6709", "\u908a\u6b3e", "\u54ea\u4e9b")
NOT_COVERED = {"\u96de\u86cb", "\u85af\u689d", "\u9bae\u5976", "M&M", "m&m"}
AMBIGUOUS = {"\u7cd6", "\u6cb9", "\u7c73", "\u9eb5", "\u9762", "\u5976", "\u6c34", "\u7d19", "\u91ac", "\u7c89", "\u7d19\u5dfe"}
CATEGORY_TERMS = {"\u6d17\u982d\u6c34", "\u7259\u818f", "\u6fd5\u7d19\u5dfe", "\u6731\u53e4\u529b\u98f2\u54c1", "\u98df\u6cb9", "\u98f2\u54c1", "\u85af\u7247"}

NON_SHOPPING_EXACT = {
    "\u4f60\u597d",
    "hello",
    "hi",
    "hey",
    "\u65e9\u6668",
    "\u65e9\u5b89",
    "\u665a\u5b89",
    "\u8b1d\u8b1d",
    "thanks",
    "thank you",
    "\u4f60\u662f\u8ab0",
    "\u4f60\u53ef\u4ee5\u505a\u4ec0\u9ebc",
    "\u4eca\u5929\u5929\u6c23\u5982\u4f55",
    "\u5929\u6c23",
    "\u5e6b\u6211\u505a\u529f\u8ab2",
    "\u8b1b\u7b11\u8a71",
}
NON_SHOPPING_CONTAINS = (
    "\u5929\u6c23",
    "\u505a\u529f\u8ab2",
    "\u8b1b\u7b11\u8a71",
    "\u4f60\u662f\u8ab0",
    "\u4f60\u53ef\u4ee5\u505a\u4ec0\u9ebc",
)
AMBIGUOUS_LABEL = "\u8acb\u5148\u8aaa\u660e\u4f60\u60f3\u627e\u54ea\u4e00\u985e\u5546\u54c1\u3002"
BUY_PREFIXES = (
    "\u6211\u60f3\u8cb7",
    "\u60f3\u8cb7",
    "\u6211\u8981\u8cb7",
    "\u8cb7",
    "\u60f3\u6415",
    "\u6415",
)


def _goal(query: str) -> str:
    text = str(query or "")
    if any(token in text for token in CHEAPEST_TOKENS):
        return "cheapest"
    if any(token in text for token in LIST_TOKENS):
        return "list_options"
    if "\u5e7e\u9322" in text or "\u591a\u5c11\u9322" in text:
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
    for prefix in BUY_PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
    for token in ("\u6700\u5e73", "\u5e7e\u9322", "\u591a\u5c11\u9322", *CHEAPEST_TOKENS):
        text = text.replace(token, "")
    text = re.sub(r"^[\s,\uff0c\u3002\uff1f\uff01!?]+", "", text)
    text = text.lstrip("\u7684")
    return text.strip(" ,\uff0c\u3002\uff1f\uff01!?")


def _normalized_terms(terms: set[str] | tuple[str, ...]) -> set[str]:
    return {normalize_product_name_for_lookup(term) for term in terms}


NORMALIZED_NOT_COVERED = _normalized_terms(NOT_COVERED)
NORMALIZED_AMBIGUOUS = _normalized_terms(AMBIGUOUS)
NORMALIZED_CATEGORY_TERMS = _normalized_terms(CATEGORY_TERMS)
NORMALIZED_NON_SHOPPING_EXACT = _normalized_terms(NON_SHOPPING_EXACT)


def _is_non_shopping_query(query: str) -> bool:
    text = str(query or "").strip()
    if not text:
        return False
    lowered = text.lower()
    normalized = normalize_product_name_for_lookup(text)
    if text in NON_SHOPPING_EXACT or lowered in NON_SHOPPING_EXACT or normalized in NORMALIZED_NON_SHOPPING_EXACT:
        return True
    return any(token in text or token in lowered for token in NON_SHOPPING_CONTAINS)


def route_item_intent(raw_item_name: str, context: dict | None = None) -> dict:
    raw = str(raw_item_name or "").strip()
    normalized = normalize_product_name_for_lookup(raw)
    goal = _goal(str((context or {}).get("query") or raw))
    reasons: list[str] = []
    brand = next(
        (
            brand
            for brand in BRAND_TERMS
            if normalize_product_name_for_lookup(brand) == normalized
            or normalize_product_name_for_lookup(brand) in normalized
        ),
        None,
    )
    brand_index = (context or {}).get("brand_index") or {}
    mined_brand = detect_brand_query(raw, brand_index) if brand_index else {"matched": False}
    if not brand and mined_brand.get("matched"):
        brand = str(mined_brand.get("brand") or "")

    query_type = "unknown"
    confidence = "low"
    category_hint = None
    product_clues: list[str] = []
    unsupported_reason = None
    needs_clarification = False
    clarification_options: list[dict[str, Any]] = []

    if _is_non_shopping_query(raw):
        query_type = "unsupported_request"
        confidence = "high"
        unsupported_reason = "non_shopping_query"
        reasons.append("non-shopping/greeting query detected")
    elif raw in NOT_COVERED or normalized in NORMALIZED_NOT_COVERED:
        query_type = "not_covered_request"
        confidence = "high"
        unsupported_reason = "not covered by current public price catalog"
        reasons.append("explicit not-covered item")
    elif raw in AMBIGUOUS or normalized in NORMALIZED_AMBIGUOUS:
        query_type = "ambiguous_request"
        confidence = "high"
        needs_clarification = True
        clarification_options = [{"label_zh": AMBIGUOUS_LABEL, "intent_id": "clarify_generic_term"}]
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
    elif brand and normalized == normalize_product_name_for_lookup(brand) and (
        not mined_brand.get("matched") or mined_brand.get("confidence") == "high"
    ):
        query_type = "brand_search"
        confidence = "high" if (not mined_brand.get("matched") or mined_brand.get("confidence") == "high") else "medium"
        reasons.append("brand-only query")
    elif brand and should_try_direct_product_search(raw) and normalized != normalize_product_name_for_lookup(brand):
        query_type = "partial_product_search"
        confidence = "high"
        product_clues = [brand]
        reasons.append("brand plus product/flavor clues")
    elif "\u6fd5\u7d19\u5dfe" in raw and ("BB" in raw.upper() or "\u5b30" in raw or "baby" in raw.lower()):
        query_type = "category_search"
        confidence = "high"
        category_hint = "wet_wipe"
        reasons.append("wet wipe category clue")
    elif raw in CATEGORY_TERMS or normalized in NORMALIZED_CATEGORY_TERMS:
        query_type = "category_search"
        confidence = "high"
        category_hint = raw
        reasons.append("known category term")
    elif should_try_direct_product_search(raw) and len(normalized) >= 5:
        query_type = "direct_product_search"
        confidence = "medium"
        reasons.append("specific product-like query")
    else:
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


def classify_query_type(query: str, raw_items: list[dict] | None = None, context: dict | None = None) -> dict:
    text = str(query or "").strip()
    clean = _clean_single_query(text)
    if _is_non_shopping_query(text):
        return {
            "query_type": "unsupported_request",
            "confidence": "high",
            "unsupported_reason": "non_shopping_query",
            "reasons": ["non-shopping/greeting query detected"],
        }
    if any(token in text for token in SUBJECTIVE_TOKENS):
        return {"query_type": "subjective_recommendation", "confidence": "high", "reasons": ["subjective token in query"]}
    if any(token in text for token in UNSUPPORTED_TOKENS):
        return {"query_type": "unsupported_request", "confidence": "high", "reasons": ["unsupported token in query"]}
    items = raw_items or [{"raw": clean or text, "quantity": 1, "unit": None}]
    if len(items) > 1:
        return {"query_type": "basket_optimization", "confidence": "high", "reasons": ["multiple shopping items"]}
    item_decision = route_item_intent(str(items[0].get("raw") or clean or text), {"query": text, **items[0], **(context or {})})
    result = {
        "query_type": item_decision["query_type"],
        "confidence": item_decision["confidence"],
        "reasons": list(item_decision.get("reasons") or []),
    }
    if item_decision.get("unsupported_reason"):
        result["unsupported_reason"] = item_decision["unsupported_reason"]
    return result


def build_router_decision(
    query_type: str,
    confidence: str,
    raw_items: list[dict],
    reasons: list[str],
    clarification_options: list[dict] | None = None,
) -> dict:
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


def route_user_query(
    query: str,
    planner_output: dict | None = None,
    use_llm_router: bool = False,
    llm_router_options: dict | None = None,
) -> dict:
    context_options = llm_router_options or {}
    planner_items = _raw_items_from_planner(query, planner_output)
    clean_query = _clean_single_query(query)
    if (
        len(planner_items) == 1
        and clean_query
        and clean_query != planner_items[0].get("raw")
        and not re.search(r"[\s,\uff0c\u3002\uff1f\uff01!?]", clean_query)
    ):
        planner_items = [{"raw": clean_query, "quantity": planner_items[0].get("quantity") or 1, "unit": planner_items[0].get("unit")}]

    routed_items = [route_item_intent(str(item.get("raw") or ""), {"query": query, **item, **context_options}) for item in planner_items]
    classification = classify_query_type(query, routed_items, context_options)
    query_type = classification["query_type"]
    confidence = classification["confidence"]
    reasons = [*classification.get("reasons", [])]
    for item in routed_items:
        reasons.extend(item.get("reasons") or [])
    unsupported = classification.get("unsupported_reason") or next(
        (item.get("unsupported_reason") for item in routed_items if item.get("unsupported_reason")),
        None,
    )
    decision = build_router_decision(query_type, confidence, routed_items, list(dict.fromkeys(reasons)))
    decision.update(
        {
            "query": query,
            "unsupported_reason": unsupported,
            "clarification_options": [
                option for item in routed_items for option in (item.get("clarification_options") or [])
            ],
            "warnings": ["llm router requested but not enabled in MVP"] if use_llm_router else [],
        }
    )
    return decision
