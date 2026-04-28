from __future__ import annotations

import re
from typing import Any


def _u(value: str) -> str:
    return value


KEYWORD_EXPANSIONS: dict[str, list[str]] = {
    "\u7c73": ["\u7c73", "\u767d\u7c73", "\u73cd\u73e0\u7c73", "\u9999\u7c73", "\u7d72\u82d7\u7c73"],
    "\u6d17\u982d\u6c34": ["\u6d17\u982d\u6c34", "\u6d17\u9aee\u9732", "\u6d17\u9aee\u6c34", "shampoo"],
    "\u7d19\u5dfe": ["\u7d19\u5dfe", "\u62bd\u7d19", "\u5ec1\u7d19", "\u5377\u7d19", "\u76d2\u88dd\u7d19\u5dfe", "\u62b9\u624b\u7d19"],
    "\u725b\u5976": ["\u725b\u5976", "\u9bae\u5976", "\u5976"],
    "\u98df\u6cb9": ["\u98df\u6cb9", "\u82b1\u751f\u6cb9", "\u7c9f\u7c73\u6cb9", "\u82a5\u82b1\u7c7d\u6cb9", "\u6a44\u6b16\u6cb9"],
    "\u7259\u818f": ["\u7259\u818f"],
    "\u6d17\u8863\u6db2": ["\u6d17\u8863\u6db2", "\u6d17\u8863\u5291", "\u6d17\u8863\u9732"],
}

NEGATIVE_TERMS: dict[str, list[str]] = {
    "\u7c73": ["\u7c73\u7c89", "\u7389\u7c73", "\u7c73\u9905", "\u7c73\u901a", "\u7c73\u7dda", "\u7cd9\u7c73\u8336"],
    "\u7d19\u5dfe": ["\u6fd5\u7d19\u5dfe", "\u6d88\u6bd2\u6fd5\u7d19\u5dfe", "\u842c\u7528\u6d88\u6bd2", "\u6fd5\u5dfe"],
    "\u6d17\u982d\u6c34": ["\u6c90\u6d74\u9732", "\u6d17\u624b\u6db2", "\u8b77\u9aee\u7d20"],
    "\u725b\u5976": ["\u5976\u7c89", "\u7149\u5976", "\u6930\u5976", "\u8c46\u5976"],
}

RICE_POSITIVE_TERMS = ("\u767d\u7c73", "\u73cd\u73e0\u7c73", "\u9999\u7c73", "\u7d72\u82d7\u7c73", "\u8309\u8389\u9999\u7c73", "\u6cf0\u570b\u9999\u7c73")
SHAMPOO_POSITIVE_TERMS = ("\u6d17\u982d\u6c34", "\u6d17\u9aee\u9732", "\u6d17\u9aee\u6c34", "shampoo")
TISSUE_POSITIVE_TERMS = ("\u7d19\u5dfe", "\u62bd\u7d19", "\u5377\u7d19", "\u5ec1\u7d19", "\u76d2\u88dd\u7d19\u5dfe", "\u62b9\u624b\u7d19")


def normalize_keyword(keyword: str) -> str:
    return str(keyword or "").strip().casefold()


def _canonical_keyword(keyword: str) -> str:
    normalized = normalize_keyword(keyword)
    for canonical, terms in KEYWORD_EXPANSIONS.items():
        if normalized == normalize_keyword(canonical) or normalized in {normalize_keyword(term) for term in terms}:
            return canonical
    return str(keyword or "").strip()


def expand_keyword(keyword: str) -> list[str]:
    canonical = _canonical_keyword(keyword)
    terms = KEYWORD_EXPANSIONS.get(canonical, [str(keyword or "").strip()])
    seen: set[str] = set()
    expanded: list[str] = []
    for term in terms:
        normalized = normalize_keyword(term)
        if normalized and normalized not in seen:
            seen.add(normalized)
            expanded.append(term)
    return expanded


def negative_terms_for_keyword(keyword: str) -> list[str]:
    return NEGATIVE_TERMS.get(_canonical_keyword(keyword), [])


def _contains(text: Any, term: str) -> bool:
    normalized = normalize_keyword(term)
    return bool(normalized) and normalized in normalize_keyword(str(text or ""))


def _has_any(text: Any, terms: tuple[str, ...] | list[str]) -> bool:
    return any(_contains(text, term) for term in terms)


def _parse_size(package_quantity: Any) -> tuple[float | None, str]:
    text = normalize_keyword(str(package_quantity or "")).replace(" ", "")
    match = re.search(r"(\d+(?:\.\d+)?)(?:kg|公斤|\u516c\u65a4)", text)
    if match:
        return float(match.group(1)), "kg"
    match = re.search(r"(\d+(?:\.\d+)?)(?:g|克|\u514b)", text)
    if match:
        return float(match.group(1)) / 1000.0, "kg"
    match = re.search(r"(\d+(?:\.\d+)?)(?:ml|毫升|\u6beb\u5347)", text)
    if match:
        return float(match.group(1)), "ml"
    match = re.search(r"(\d+(?:\.\d+)?)(?:l|升|\u5347)", text)
    if match:
        return float(match.group(1)) * 1000.0, "ml"
    return None, ""


def package_preference_score(keyword: str, product_name: Any, package_quantity: Any) -> float:
    canonical = _canonical_keyword(keyword)
    name = normalize_keyword(str(product_name or ""))
    package = normalize_keyword(str(package_quantity or ""))
    size, unit = _parse_size(package)
    score = 0.0

    if canonical == "\u7c73":
        if _has_any(name, RICE_POSITIVE_TERMS):
            score += 8.0
        if _has_any(name, NEGATIVE_TERMS["\u7c73"]):
            score -= 25.0
        if unit == "kg" and size is not None:
            if size in {5.0, 8.0, 10.0, 25.0}:
                score += 10.0
            elif 4.0 <= size <= 10.0:
                score += 7.0
            elif size == 1.0:
                score += 2.0
            elif size < 1.0:
                score -= 4.0
        return score

    if canonical == "\u6d17\u982d\u6c34":
        if _has_any(name, SHAMPOO_POSITIVE_TERMS):
            score += 10.0
        if _has_any(name, NEGATIVE_TERMS["\u6d17\u982d\u6c34"]):
            score -= 18.0
        if unit == "ml" and size is not None:
            if 500 <= size <= 1000:
                score += 8.0
            elif 300 <= size < 500:
                score += 4.0
            elif size < 200:
                score -= 2.0
        return score

    if canonical == "\u7d19\u5dfe":
        if _has_any(name, TISSUE_POSITIVE_TERMS):
            score += 8.0
        if _has_any(name, NEGATIVE_TERMS["\u7d19\u5dfe"]):
            score -= 22.0
        if _has_any(package, ("10\u5377", "12\u5377", "5\u5305", "6\u5305")) or _has_any(name, ("\u62bd", "\u5377\u7d19", "\u5ec1\u7d19")):
            score += 7.0
        return score

    return score


def candidate_text_match_score(keyword: str, product_name: Any, package_quantity: Any = "", category_name: Any = "") -> float:
    normalized_keyword = normalize_keyword(keyword)
    product = normalize_keyword(str(product_name or ""))
    category = normalize_keyword(str(category_name or ""))
    score = 0.0

    if normalized_keyword and normalized_keyword in product:
        score += 8.0
    if normalized_keyword and normalized_keyword in category:
        score += 4.0

    expanded = expand_keyword(keyword)
    for term in expanded:
        term_norm = normalize_keyword(term)
        if not term_norm:
            continue
        if term_norm in product:
            score += 6.0
        elif term_norm in category:
            score += 3.0

    for term in negative_terms_for_keyword(keyword):
        if _contains(product, term):
            score -= 18.0
        elif _contains(category, term):
            score -= 8.0

    score += package_preference_score(keyword, product_name, package_quantity)
    return score
