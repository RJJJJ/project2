from __future__ import annotations

from typing import Any

from services.product_direct_search import FLAVOR_TOKENS, normalize_product_name_for_lookup
from services.product_intent_taxonomy import PRODUCT_INTENTS


DEFAULT_RAG_V2_WEIGHTS = {
    "exact_name": 30,
    "normalized_exact": 28,
    "query_containment": 20,
    "brand_match": 12,
    "flavor_match": 10,
    "intent_positive": 8,
    "category_allowlist": 3,
    "synonym": 6,
    "token_overlap": 4,
    "negative_penalty": -100,
    "missing_flavor_penalty": -15,
}
HIGH_RISK_SHORT = {"糖", "油", "米", "麵", "面", "奶", "水", "紙", "紙巾", "朱古力", "飲品", "雞蛋", "蛋"}


def _norm(value: Any) -> str:
    return normalize_product_name_for_lookup(str(value or ""))


def _terms(intent_id: str | None, key: str) -> list[str]:
    if not intent_id or intent_id not in PRODUCT_INTENTS:
        return []
    values = PRODUCT_INTENTS[intent_id].get(key) or []
    return [str(value) for value in values if str(value or "").strip()]


def _query_tokens(query: str) -> list[str]:
    text = _norm(query)
    tokens = [text] if text else []
    for token in FLAVOR_TOKENS:
        nt = _norm(token)
        if nt and nt in text:
            tokens.append(nt)
    # split on ASCII spaces before normalization destroys them
    for part in str(query or "").replace("、", " ").replace(",", " ").split():
        npart = _norm(part)
        if npart:
            tokens.append(npart)
    return list(dict.fromkeys(tokens))


def _base_candidate(product: dict[str, Any], score: float, features: dict[str, bool], matched_terms: list[str], penalties: list[str]) -> dict[str, Any]:
    return {
        "product_oid": product.get("product_oid"),
        "product_name": product.get("product_name"),
        "category_id": product.get("category_id"),
        "category_name": product.get("category_name"),
        "package_quantity": product.get("package_quantity"),
        "retrieval_mode": "rag_v2",
        "rag_score": round(score, 4),
        "match_score": round(min(0.99, max(0.0, score / 60)), 4),
        "rag_features": features,
        "matched_terms": list(dict.fromkeys(matched_terms)),
        "penalties": penalties,
        "explanation_zh": "",
    }


def _score_product(
    product: dict[str, Any],
    query: str,
    intent_id: str | None,
    brand: str | None,
    category_hint: str | None,
    weights: dict[str, float],
) -> dict[str, Any] | None:
    name_raw = str(product.get("product_name") or "")
    category_raw = str(product.get("category_name") or "")
    name = _norm(name_raw)
    category = _norm(category_raw)
    q = _norm(query)
    brand_norm = _norm(brand or "")
    hint_norm = _norm(category_hint or "")
    tokens = _query_tokens(query)
    positives = [_norm(term) for term in [*_terms(intent_id, "positive_terms"), *_terms(intent_id, "example_queries")] if _norm(term)]
    negatives = [_norm(term) for term in _terms(intent_id, "negative_terms") if _norm(term)]
    allow = [_norm(term) for term in _terms(intent_id, "category_allowlist") if _norm(term)]
    synonyms = [_norm(term) for term in _terms(intent_id, "synonyms") if _norm(term)]
    features = {
        "exact_name": False,
        "normalized_exact": False,
        "query_containment": False,
        "brand_match": False,
        "flavor_match": False,
        "intent_positive": False,
        "category_allowlist": False,
        "synonym": False,
        "token_overlap": False,
    }
    matched: list[str] = []
    penalties: list[str] = []
    score = 0.0

    if q and name_raw == str(query):
        features["exact_name"] = True
        score += weights["exact_name"]
        matched.append(str(query))
    if q and name == q:
        features["normalized_exact"] = True
        score += weights["normalized_exact"]
        matched.append(q)
    if q and (q in name or (len(name) >= 4 and name in q)):
        features["query_containment"] = True
        score += weights["query_containment"]
        matched.append(q if q in name else name)
    if brand_norm and brand_norm in name:
        features["brand_match"] = True
        score += weights["brand_match"]
        matched.append(brand_norm)
    if hint_norm and (hint_norm in name or hint_norm in category):
        features["synonym"] = True
        score += weights["synonym"]
        matched.append(hint_norm)
    for term in positives:
        if term and (term in name or term in category):
            features["intent_positive"] = True
            score += weights["intent_positive"]
            matched.append(term)
            break
    for term in synonyms:
        if term and (term in name or term in category or term in q):
            features["synonym"] = True
            score += weights["synonym"]
            matched.append(term)
            break
    if any(term and (term in name or term in category) for term in allow):
        features["category_allowlist"] = True
        score += weights["category_allowlist"]
    for term in negatives:
        if term and term in name:
            score += weights["negative_penalty"]
            penalties.append(f"negative:{term}")
    query_flavors = [_norm(token) for token in FLAVOR_TOKENS if _norm(token) and _norm(token) in q]
    if query_flavors:
        matched_flavors = [term for term in query_flavors if term in name]
        if matched_flavors:
            features["flavor_match"] = True
            score += weights["flavor_match"] * len(matched_flavors)
            matched.extend(matched_flavors)
        missing = [term for term in query_flavors if term not in name]
        if missing:
            score += weights["missing_flavor_penalty"] * len(missing)
            penalties.extend([f"missing_flavor:{term}" for term in missing])
    overlap = [token for token in tokens if token and len(token) >= 2 and token in name]
    if overlap:
        features["token_overlap"] = True
        score += weights["token_overlap"] * min(len(overlap), 3)
        matched.extend(overlap)

    evidence_keys = {"exact_name", "normalized_exact", "query_containment", "brand_match", "flavor_match", "intent_positive", "synonym", "token_overlap"}
    has_actual_evidence = any(features[key] for key in evidence_keys)
    if intent_id and features["category_allowlist"] and not has_actual_evidence:
        return None
    if q in {_norm(term) for term in HIGH_RISK_SHORT} and not intent_id and not brand_norm:
        return None
    if score <= 0:
        return None
    candidate = _base_candidate(product, score, features, matched, penalties)
    candidate["explanation_zh"] = explain_rag_v2_candidate(candidate)["explanation_zh"]
    return candidate


def rag_v2_retrieve_candidates(
    products: list[dict],
    query: str,
    intent_id: str | None = None,
    brand: str | None = None,
    category_hint: str | None = None,
    limit: int = 20,
    weights: dict | None = None,
) -> list[dict]:
    merged_weights = {**DEFAULT_RAG_V2_WEIGHTS, **(weights or {})}
    scored: list[dict[str, Any]] = []
    for product in products:
        candidate = _score_product(product, query, intent_id, brand, category_hint, merged_weights)
        if candidate is not None:
            scored.append(candidate)
    scored.sort(key=lambda item: (-float(item.get("rag_score") or 0), str(item.get("product_name") or ""), str(item.get("product_oid") or "")))
    return scored[: max(0, int(limit))]


def explain_rag_v2_candidate(candidate: dict) -> dict:
    features = candidate.get("rag_features") or {}
    parts: list[str] = []
    if features.get("brand_match"):
        parts.append("品牌相符")
    if features.get("flavor_match"):
        parts.append("口味相符")
    if features.get("query_containment") or features.get("normalized_exact") or features.get("exact_name"):
        parts.append("名稱相符")
    if features.get("intent_positive") or features.get("synonym"):
        parts.append("類別關鍵詞相符")
    if features.get("token_overlap"):
        parts.append("字詞重疊")
    if candidate.get("penalties"):
        parts.append("已套用風險扣分")
    return {"explanation_zh": "、".join(parts) if parts else "基於保守詞彙相似度排序"}
