from __future__ import annotations

from typing import Any

from services.product_intent_taxonomy import PRODUCT_INTENTS


def _text(value: Any) -> str:
    return str(value or "")


def _category_id(product: dict[str, Any]) -> int | None:
    value = product.get("category_id")
    try:
        return int(value) if value is not None and value != "" else None
    except (TypeError, ValueError):
        return None


def _contains(text: str, term: str) -> bool:
    return term.casefold() in text.casefold()


def _score(product_name: str, matched_terms: list[str]) -> tuple[int, int, int, str]:
    exact_bonus = 1 if any(product_name.casefold() == term.casefold() for term in matched_terms) else 0
    phrase_strength = max((len(term) for term in matched_terms), default=0)
    return (-len(matched_terms), -exact_bonus, -phrase_strength, product_name)


def retrieve_candidates_by_intent(
    products: list[dict[str, Any]],
    intent_id: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    intent = PRODUCT_INTENTS.get(intent_id)
    if not intent:
        return []

    positive_terms = [str(term) for term in intent.get("positive_terms", [])]
    negative_terms = [str(term) for term in intent.get("negative_terms", [])]
    allowlist = {int(item) for item in intent.get("category_allowlist", []) if item is not None}

    candidates: list[dict[str, Any]] = []
    for product in products:
        name = _text(product.get("product_name"))
        if not name:
            continue
        category_id = _category_id(product)
        if allowlist and category_id not in allowlist:
            continue
        matched_negative = [term for term in negative_terms if _contains(name, term)]
        if matched_negative:
            continue
        matched_positive = [term for term in positive_terms if _contains(name, term)]
        if not matched_positive:
            continue
        if intent_id == "chips" and not any(_contains(name, term) for term in ["薯片", "品客"]):
            continue
        candidate = dict(product)
        candidate.update(
            {
                "match_intent_id": intent_id,
                "match_reason": f"matched positive terms: {', '.join(matched_positive)}",
                "matched_positive_terms": matched_positive,
                "matched_negative_terms": [],
            }
        )
        candidates.append(candidate)

    candidates.sort(
        key=lambda item: (
            _score(_text(item.get("product_name")), item.get("matched_positive_terms") or []),
            len(_text(item.get("product_name"))),
            _text(item.get("product_oid")),
        )
    )
    return candidates[: max(0, int(limit))]
