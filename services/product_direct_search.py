from __future__ import annotations

import difflib
import re
import unicodedata
from typing import Any


HIGH_RISK_SHORT_TERMS = {
    "糖",
    "油",
    "米",
    "麵",
    "面",
    "奶",
    "水",
    "紙",
    "紙巾",
    "朱古力",
    "飲品",
    "雞蛋",
    "蛋",
}

BRAND_TERMS = {"出前一丁", "維他奶", "品客", "太古"}
FLAVOR_TOKENS = {"麻油味", "麻油", "原味", "低糖", "雞蛋", "幼面", "幼麵", "豬骨", "黑蒜油"}
GENERIC_PRODUCT_TOKENS = {
    "即食麵",
    "公仔麵",
    "薯片",
    "豆奶",
    "砂糖",
    "洗髮乳",
    "洗頭水",
    "濕紙巾",
}


def normalize_product_name_for_lookup(name: str) -> str:
    text = unicodedata.normalize("NFKC", str(name or "")).casefold()
    text = text.replace("面", "麵")
    text = re.sub(r"[\s\-_—–·．.、，,;；:：()（）\[\]【】/\\]+", "", text)
    return text


def _display_text(value: Any) -> str:
    return str(value or "")


def _tokens(raw: str) -> list[str]:
    normalized = normalize_product_name_for_lookup(raw)
    tokens: list[str] = []
    for token in sorted(BRAND_TERMS | FLAVOR_TOKENS | GENERIC_PRODUCT_TOKENS, key=len, reverse=True):
        ntoken = normalize_product_name_for_lookup(token)
        if ntoken and ntoken in normalized:
            tokens.append(ntoken)
    if not tokens and normalized:
        tokens = [normalized]
    return list(dict.fromkeys(tokens))


def _product_match_payload(product: dict[str, Any], match_type: str, direct_match_type: str, score: float, matched_terms: list[str]) -> dict[str, Any]:
    return {
        "product_oid": product.get("product_oid"),
        "product_name": product.get("product_name"),
        "category_id": product.get("category_id"),
        "category_name": product.get("category_name"),
        "package_quantity": product.get("package_quantity"),
        "match_type": match_type,
        "direct_match_type": direct_match_type,
        "match_score": round(float(score), 4),
        "matched_terms": matched_terms,
    }


def _base_result(status: str, raw_item_name: str, matches: list[dict[str, Any]], confidence: str, reason: str, risky: bool = False) -> dict[str, Any]:
    return {
        "status": status,
        "raw_item_name": raw_item_name,
        "matches": matches,
        "confidence": confidence,
        "reason": reason,
        "risky": risky,
    }


def should_try_direct_product_search(raw_item_name: str) -> bool:
    normalized = normalize_product_name_for_lookup(raw_item_name)
    if not normalized:
        return False
    if normalized in {normalize_product_name_for_lookup(term) for term in HIGH_RISK_SHORT_TERMS}:
        return False
    if len(normalized) <= 1:
        return False
    if len(normalized) <= 2 and not any(normalize_product_name_for_lookup(brand) in normalized for brand in BRAND_TERMS):
        return False
    return True


def _score_direct(product: dict[str, Any], raw_item_name: str) -> tuple[float, str, list[str]]:
    query = normalize_product_name_for_lookup(raw_item_name)
    name = normalize_product_name_for_lookup(_display_text(product.get("product_name")))
    if not query or not name:
        return 0.0, "no_match", []
    query_tokens = _tokens(raw_item_name)
    matched_terms = [token for token in query_tokens if token in name]
    flavor_terms = [normalize_product_name_for_lookup(token) for token in FLAVOR_TOKENS if normalize_product_name_for_lookup(token) in query]
    missing_flavors = [token for token in flavor_terms if token not in name]

    if name == query:
        return 1.0, "exact_match", matched_terms or [query]
    if normalize_product_name_for_lookup(_display_text(product.get("product_name"))) == query:
        return 0.99, "normalized_exact_match", matched_terms or [query]
    if query in name:
        score = 0.95
        if missing_flavors:
            score -= 0.35 * len(missing_flavors)
        return max(score, 0.0), "partial_match", matched_terms or [query]
    if name in query and len(name) >= 4:
        score = 0.92
        if missing_flavors:
            score -= 0.35 * len(missing_flavors)
        return max(score, 0.0), "partial_match", matched_terms or [name]

    coverage = len(matched_terms) / max(1, len(query_tokens))
    if coverage:
        score = 0.55 + (0.35 * coverage)
        if missing_flavors:
            score -= 0.35 * len(missing_flavors)
        return max(score, 0.0), "token_coverage", matched_terms

    if len(query) >= 5:
        ratio = difflib.SequenceMatcher(None, query, name).ratio()
        if ratio >= 0.82:
            return ratio * 0.82, "fuzzy_match", []
    return 0.0, "no_match", []


def search_direct_products(products: list[dict[str, Any]], raw_item_name: str, limit: int = 10) -> dict[str, Any]:
    if not should_try_direct_product_search(raw_item_name):
        return _base_result("no_match", raw_item_name, [], "low", "direct search disabled for high-risk or short query", risky=True)

    scored: list[dict[str, Any]] = []
    for product in products:
        score, match_type, matched_terms = _score_direct(product, raw_item_name)
        if score <= 0:
            continue
        scored.append(_product_match_payload(product, "direct_product", match_type, score, matched_terms))

    scored.sort(key=lambda item: (-float(item["match_score"]), len(str(item.get("product_name") or "")), str(item.get("product_oid") or "")))
    matches = scored[: max(0, int(limit))]
    if not matches:
        return _base_result("no_match", raw_item_name, [], "low", "no direct product match")

    top_score = float(matches[0]["match_score"])
    close = [m for m in matches if top_score - float(m["match_score"]) <= 0.03]
    if top_score >= 0.97:
        status = "exact_match" if matches[0]["direct_match_type"] == "exact_match" else "normalized_exact_match"
        return _base_result(status, raw_item_name, matches, "high", f"{matches[0]['direct_match_type']} with high confidence")
    if top_score >= 0.90:
        return _base_result("partial_match", raw_item_name, matches, "high", "unique high-confidence partial match")
    if top_score >= 0.78:
        return _base_result("multiple_candidates", raw_item_name, matches, "medium", "multiple or medium-confidence direct candidates")
    return _base_result("fuzzy_match", raw_item_name, matches, "low", "low-confidence fuzzy candidates", risky=True)


def search_brand_products(products: list[dict[str, Any]], brand_or_name: str, category_hint: str | None = None, limit: int = 20) -> dict[str, Any]:
    query = normalize_product_name_for_lookup(brand_or_name)
    if not query:
        return _base_result("no_match", brand_or_name, [], "low", "empty brand query")
    category_norm = normalize_product_name_for_lookup(category_hint or "")
    matches: list[dict[str, Any]] = []
    for product in products:
        name = normalize_product_name_for_lookup(_display_text(product.get("product_name")))
        category_name = normalize_product_name_for_lookup(_display_text(product.get("category_name")))
        if query not in name:
            continue
        if category_norm and category_norm not in category_name and category_norm not in name:
            continue
        score = 0.85 if name.startswith(query) else 0.78
        matches.append(_product_match_payload(product, "brand_product", "brand_contains", score, [query]))
    matches.sort(key=lambda item: (-float(item["match_score"]), str(item.get("product_name") or ""), str(item.get("product_oid") or "")))
    matches = matches[: max(0, int(limit))]
    if not matches:
        return _base_result("no_match", brand_or_name, [], "low", "no brand products found")
    confidence = "high" if len(matches) <= 10 else "medium"
    return _base_result("multiple_candidates", brand_or_name, matches, confidence, "brand/name containment search")
