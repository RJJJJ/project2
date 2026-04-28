from __future__ import annotations

import unicodedata
from typing import Any

from services.product_intent_taxonomy import (
    AMBIGUOUS_QUERIES,
    NOT_COVERED_QUERIES,
    PRODUCT_INTENTS,
    QUERY_SYNONYMS,
)


def normalize_query_text(text: str) -> str:
    return unicodedata.normalize("NFKC", str(text or "")).strip()


def _display(intent_id: str) -> str:
    return str(PRODUCT_INTENTS.get(intent_id, {}).get("display_name_zh") or intent_id)


def _base_result(raw_item_name: str, normalized: str) -> dict[str, Any]:
    return {
        "raw_item_name": raw_item_name,
        "normalized_item_name": normalized,
        "status": "unknown",
        "intent_id": None,
        "intent_options": [],
        "reason": "",
        "message_zh": "",
    }


def _covered(raw_item_name: str, normalized: str, intent_id: str, reason: str) -> dict[str, Any]:
    result = _base_result(raw_item_name, normalized)
    result.update(
        {
            "status": "covered",
            "intent_id": intent_id,
            "reason": reason,
            "message_zh": f"已理解「{normalized}」為「{_display(intent_id)}」。",
        }
    )
    return result


def _ambiguous(raw_item_name: str, normalized: str, options: list[str], reason: str) -> dict[str, Any]:
    result = _base_result(raw_item_name, normalized)
    labels = " / ".join(_display(option) for option in options)
    result.update(
        {
            "status": "ambiguous",
            "intent_options": options,
            "reason": reason,
            "message_zh": f"你想找的是「{labels}」哪一類？",
        }
    )
    return result


def _not_covered(raw_item_name: str, normalized: str) -> dict[str, Any]:
    result = _base_result(raw_item_name, normalized)
    result.update(
        {
            "status": "not_covered",
            "reason": "explicit_not_covered_query",
            "message_zh": f"目前消委會公開監測資料暫未收錄「{normalized}」的可比較價格。這不代表超市沒有售賣，只代表本系統暫時沒有公開監測價格資料。",
        }
    )
    return result


def _term_matches(query: str, term: str) -> bool:
    query_fold = query.casefold()
    term_fold = term.casefold()
    return bool(query_fold and term_fold and (query_fold == term_fold or term_fold in query_fold or query_fold in term_fold))


def resolve_product_intent(raw_item_name: str) -> dict[str, Any]:
    normalized = normalize_query_text(raw_item_name)
    result = _base_result(raw_item_name, normalized)
    if not normalized:
        result.update({"reason": "empty_query", "message_zh": "未能識別商品名稱。"})
        return result

    if normalized in NOT_COVERED_QUERIES or normalized.casefold() in {item.casefold() for item in NOT_COVERED_QUERIES}:
        return _not_covered(raw_item_name, normalized)

    if normalized in AMBIGUOUS_QUERIES:
        return _ambiguous(raw_item_name, normalized, AMBIGUOUS_QUERIES[normalized], "explicit_ambiguous_query")

    synonym_intent = QUERY_SYNONYMS.get(normalized) or QUERY_SYNONYMS.get(normalized.casefold())
    if synonym_intent:
        return _covered(raw_item_name, normalized, synonym_intent, "query_synonym")

    matched_intents: list[str] = []
    for intent_id, intent in PRODUCT_INTENTS.items():
        for term in intent.get("positive_terms", []):
            if _term_matches(normalized, str(term)):
                matched_intents.append(intent_id)
                break

    matched_intents = list(dict.fromkeys(matched_intents))
    if len(matched_intents) == 1:
        return _covered(raw_item_name, normalized, matched_intents[0], "positive_term_unique_match")
    if len(matched_intents) > 1:
        return _ambiguous(raw_item_name, normalized, matched_intents, "positive_term_multiple_matches")

    result.update(
        {
            "reason": "no_intent_match",
            "message_zh": f"暫時未能判斷「{normalized}」屬於哪一類商品。",
        }
    )
    return result
