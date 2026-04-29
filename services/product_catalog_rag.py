from __future__ import annotations

import re
from typing import Any

from services.product_intent_taxonomy import NOT_COVERED_QUERIES, PRODUCT_INTENTS, QUERY_SYNONYMS


_TOKEN_RE = re.compile(r"[A-Za-z0-9&']+|[\u4e00-\u9fff]+")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _category_id(product: dict[str, Any]) -> int | None:
    value = product.get("category_id")
    try:
        return int(value) if value is not None and value != "" else None
    except (TypeError, ValueError):
        return None


def _tokens(text: str) -> list[str]:
    return [token.casefold() for token in _TOKEN_RE.findall(str(text or "")) if token]


def _contains_term(text: str, term: str) -> bool:
    return str(term or "").casefold() in str(text or "").casefold()


def _intent_tags_for_product(product: dict[str, Any]) -> list[str]:
    name = _text(product.get("product_name"))
    category_id = _category_id(product)
    tags: list[str] = []
    for intent_id, intent in PRODUCT_INTENTS.items():
        allowlist = {int(item) for item in intent.get("category_allowlist", []) if item is not None}
        if allowlist and category_id not in allowlist:
            continue
        negative_terms = [str(term) for term in intent.get("negative_terms", [])]
        if any(_contains_term(name, term) for term in negative_terms):
            continue
        positive_terms = [str(term) for term in intent.get("positive_terms", [])]
        if positive_terms and any(_contains_term(name, term) for term in positive_terms):
            tags.append(intent_id)
    return tags


def build_product_catalog_documents(products: list[dict]) -> list[dict]:
    documents: list[dict] = []
    for product in products:
        name = _text(product.get("product_name"))
        if not name:
            continue
        category_name = _text(product.get("category_name"))
        package_quantity = _text(product.get("package_quantity"))
        intent_tags = _intent_tags_for_product(product)
        search_text_parts = [name, category_name, package_quantity]
        if intent_tags:
            search_text_parts.extend(str(PRODUCT_INTENTS[intent_id].get("display_name_zh") or intent_id) for intent_id in intent_tags if intent_id in PRODUCT_INTENTS)
        documents.append(
            {
                "product_oid": product.get("product_oid"),
                "product_name": name,
                "category_id": product.get("category_id"),
                "category_name": category_name,
                "package_quantity": package_quantity,
                "intent_tags": intent_tags,
                "search_text": " ".join(part for part in search_text_parts if part),
            }
        )
    return documents


def _query_is_not_covered(query: str) -> bool:
    normalized = _text(query)
    return normalized in NOT_COVERED_QUERIES or normalized.casefold() in {item.casefold() for item in NOT_COVERED_QUERIES}


def rag_assisted_retrieve_candidates(
    products: list[dict],
    query: str,
    intent_id: str | None = None,
    limit: int = 20,
) -> list[dict]:
    if _query_is_not_covered(query):
        return []

    documents = build_product_catalog_documents(products)
    query_text = _text(query)
    query_tokens = _tokens(query_text)
    normalized_query = query_text.casefold()
    synonym_intent = QUERY_SYNONYMS.get(query_text) or QUERY_SYNONYMS.get(query_text.casefold())
    intent = PRODUCT_INTENTS.get(intent_id) if intent_id else None
    allowlist = {int(item) for item in (intent or {}).get("category_allowlist", []) if item is not None}
    positive_terms = [str(term) for term in (intent or {}).get("positive_terms", [])]
    negative_terms = [str(term) for term in (intent or {}).get("negative_terms", [])]

    scored: list[dict[str, Any]] = []
    for product, document in zip(products, documents):
        name = _text(document.get("product_name"))
        category_name = _text(document.get("category_name"))
        search_text = _text(document.get("search_text"))
        product_tokens = set(_tokens(search_text))
        category_id = _category_id(product)

        if allowlist and category_id not in allowlist:
            continue
        if intent_id and any(_contains_term(name, term) for term in negative_terms):
            continue

        score = 0.0
        reasons: list[str] = []
        matched_terms: list[str] = []

        if normalized_query and name.casefold() == normalized_query:
            score += 12.0
            reasons.append("exact product name match")
        if normalized_query and normalized_query in name.casefold():
            score += 8.0
            reasons.append("query contained in product name")
        if normalized_query and normalized_query in category_name.casefold():
            score += 3.0
            reasons.append("query matched category name")

        for token in query_tokens:
            if token in product_tokens:
                score += 2.5
                matched_terms.append(token)
        if matched_terms:
            reasons.append("matched lexical terms")

        if synonym_intent and synonym_intent in (document.get("intent_tags") or []):
            score += 4.0
            reasons.append("matched synonym intent tag")

        if intent_id and intent_id in (document.get("intent_tags") or []):
            score += 5.0
            reasons.append("matched intent tag")

        matched_positive_terms = [term for term in positive_terms if _contains_term(name, term)]
        for term in matched_positive_terms:
            score += 3.5
            matched_terms.append(term)
        if matched_positive_terms:
            reasons.append("matched intent positive terms")

        if allowlist and category_id in allowlist:
            score += 2.0
            reasons.append("category allowlist match")

        for term in negative_terms:
            if _contains_term(search_text, term):
                score -= 6.0
                reasons.append(f"negative term penalty: {term}")

        if score <= 0:
            continue

        candidate = dict(product)
        candidate.update(
            {
                "retrieval_mode": "rag_assisted",
                "rag_score": round(score, 3),
                "rag_reason": "; ".join(dict.fromkeys(reasons)),
                "matched_terms": list(dict.fromkeys(matched_terms)),
            }
        )
        scored.append(candidate)

    scored.sort(
        key=lambda item: (
            -float(item.get("rag_score") or 0),
            _text(item.get("product_name")),
            _text(item.get("product_oid")),
        )
    )
    return scored[: max(0, int(limit))]
