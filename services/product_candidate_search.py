from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from services.processed_data_loader import build_supermarket_lookup, load_price_records
from services.product_matching_rules import candidate_text_match_score, expand_keyword, is_forbidden_match, explain_match


RICE = "\u7c73"
RICE_CATEGORY = "\u7c73\u985e"
KG = "\u516c\u65a4"
ML = "\u6beb\u5347"
LITER = "\u5347"
SHAMPOO_TERMS = ("\u6d17\u982d\u6c34", "\u6d17\u9aee\u4e73", "\u6d17\u9aee\u9732", "\u500b\u4eba\u8b77\u7406\u7528\u54c1")
TISSUE_TERMS = ("\u7d19\u5dfe", "\u885b\u751f\u7d19")
REASON_HOUSEHOLD = "\u5e38\u898b\u5bb6\u5ead\u5305\u88dd\uff0c\u8f03\u9069\u5408\u65e5\u5e38\u63a1\u8cfc"
REASON_COVERAGE = "\u8f03\u591a\u8d85\u5e02\u6709\u552e\uff0c\u50f9\u683c\u53ef\u6bd4\u8f03\u6027\u8f03\u9ad8"
REASON_CHEAPEST = "\u5019\u9078\u4e2d\u6700\u4f4e\u50f9"
REASON_OVERALL = "\u7d9c\u5408\u5339\u914d\u5ea6\u8f03\u9ad8"


def _contains(value: Any, needle: str) -> bool:
    normalized = needle.strip().casefold()
    return bool(normalized) and normalized in str(value or "").casefold()


def _row_match(row: dict[str, Any], aliases: list[str]) -> str | None:
    fields = (row.get("product_name"), row.get("category_name"))
    for alias in aliases:
        if any(_contains(value, alias) for value in fields):
            return alias
    return None


def _match_score(keyword: str, matched_alias: str | None, product_name: Any, category_name: Any) -> int:
    values = [keyword, matched_alias or ""]
    product_hit = any(_contains(product_name, value) for value in values)
    category_hit = any(_contains(category_name, value) for value in values)
    score = 0
    if product_hit or category_hit:
        score += 100
    if product_hit:
        name = str(product_name or "").casefold()
        for value in values:
            normalized = value.strip().casefold()
            if normalized and (name.startswith(normalized) or name.count(normalized) >= 1):
                score += 20
                break
    elif category_hit:
        score += 50
    return score


def _has_any(value: str, needles: tuple[str, ...]) -> bool:
    return any(needle in value for needle in needles)


def _volume_ml(package_quantity: str) -> float | None:
    text = package_quantity.casefold().replace(" ", "")
    match = re.search(rf"(\d+(?:\.\d+)?)\s*(?:ml|{ML})", text)
    if match:
        return float(match.group(1))
    match = re.search(rf"(\d+(?:\.\d+)?)\s*(?:l|\u516c{LITER}|{LITER})", text)
    if match:
        return float(match.group(1)) * 1000
    return None


def _package_preference_score(keyword: str, category_name: Any, package_quantity: Any, matched_alias: str | None) -> int:
    package = str(package_quantity or "").casefold().replace(" ", "")
    category = str(category_name or "").casefold()
    keywordish = f"{keyword} {matched_alias or ''} {category}".casefold()

    if _has_any(keywordish, (RICE, RICE_CATEGORY)):
        if f"5{KG}" in package:
            return 40
        if f"10{KG}" in package:
            return 35
        if f"8{KG}" in package:
            return 25
        if f"25{KG}" in package:
            return 10
        if f"1{KG}" in package:
            return 5
        return 0

    if _has_any(keywordish, SHAMPOO_TERMS):
        volume = _volume_ml(package)
        if volume is None:
            return 0
        if volume >= 700:
            return 35
        if volume >= 500:
            return 25
        if volume <= 200:
            return 5
        return 0

    if _has_any(keywordish, TISSUE_TERMS):
        if _has_any(package, ("10\u5377", "12\u5377", "5\u5305", "6\u5305")):
            return 30
        if _has_any(package, ("\u55ae\u5305", "1\u5305", "\u5c0f\u5305")):
            return 10
        return 0

    return 0


def _price_score(min_price_mop: float) -> float:
    return max(0.0, 30.0 - min_price_mop / 10.0)


def _recommendation_reason(candidate: dict[str, Any], cheapest_price: float | None) -> str:
    package = str(candidate.get("package_quantity") or "")
    category = str(candidate.get("category_name") or "")
    keyword = str(candidate.get("keyword") or "")
    factors = candidate["ranking_factors"]

    if (RICE in keyword or RICE in category) and any(size in package for size in (f"5{KG}", f"10{KG}")):
        return REASON_HOUSEHOLD
    if factors["coverage_score"] >= 40:
        return REASON_COVERAGE
    if cheapest_price is not None and float(candidate["min_price_mop"]) == float(cheapest_price):
        return REASON_CHEAPEST
    return REASON_OVERALL


def search_product_candidates(
    date: str,
    point_code: str,
    keyword: str,
    limit: int = 10,
    processed_root: Path | None = None,
) -> list[dict[str, Any]]:
    """Search, group, and rank priced product candidates for one keyword.

    v0.1 keeps the v0 response fields and adds deterministic, explainable ranking
    signals so common household package sizes can outrank tiny low-price items.
    """
    aliases = expand_keyword(keyword)
    supermarkets = build_supermarket_lookup(date, point_code, processed_root)
    grouped: dict[Any, dict[str, Any]] = {}

    for row in load_price_records(date, point_code, processed_root):
        if row.get("price_mop") is None:
            continue
        matched_alias = _row_match(row, aliases)
        rule_score = candidate_text_match_score(keyword, row.get("product_name"), row.get("quantity"), row.get("category_name"))
        forbidden = is_forbidden_match(keyword, row.get("product_name"), row.get("category_name"))
        if matched_alias is None and rule_score <= 0:
            continue
        product_oid = row.get("product_oid")
        if product_oid is None:
            continue

        price = float(row["price_mop"])
        supermarket_oid = row.get("supermarket_oid")
        supermarket = None
        if supermarket_oid is not None:
            supermarket = supermarkets.get(int(supermarket_oid))
        supermarket_name = supermarket.get("supermarket_name") if supermarket else row.get("supermarket_name")

        candidate = grouped.setdefault(
            product_oid,
            {
                "keyword": keyword,
                "matched_alias": matched_alias or keyword,
                "product_oid": product_oid,
                "product_name": row.get("product_name"),
                "package_quantity": row.get("quantity"),
                "category_name": row.get("category_name"),
                "min_price_mop": price,
                "max_price_mop": price,
                "_store_oids": set(),
                "_sample_supermarkets": [],
                "_match_score": max(_match_score(keyword, matched_alias, row.get("product_name"), row.get("category_name")), rule_score),
                "_forbidden_match": forbidden,
            },
        )
        candidate["min_price_mop"] = min(float(candidate["min_price_mop"]), price)
        candidate["max_price_mop"] = max(float(candidate["max_price_mop"]), price)
        candidate["_match_score"] = max(
            float(candidate["_match_score"]),
            _match_score(keyword, matched_alias, row.get("product_name"), row.get("category_name")),
            rule_score,
        )
        candidate["_forbidden_match"] = bool(candidate.get("_forbidden_match")) or forbidden
        if supermarket_oid is not None:
            candidate["_store_oids"].add(supermarket_oid)
        if supermarket_name and supermarket_name not in candidate["_sample_supermarkets"]:
            candidate["_sample_supermarkets"].append(supermarket_name)

    candidates: list[dict[str, Any]] = []
    for candidate in grouped.values():
        store_count = len(candidate["_store_oids"])
        match_score = float(candidate["_match_score"])
        coverage_score = min(store_count * 5, 50)
        package_score = _package_preference_score(
            keyword,
            candidate.get("category_name"),
            candidate.get("package_quantity"),
            candidate.get("matched_alias"),
        )
        price_score = _price_score(float(candidate["min_price_mop"]))
        forbidden_match = bool(candidate.get("_forbidden_match"))
        if forbidden_match:
            match_score -= 200
        final_score = match_score + package_score + coverage_score + price_score
        ranking_factors = {
            "match_score": round(match_score, 2),
            "coverage_score": coverage_score,
            "package_preference_score": package_score,
            "price_score": round(price_score, 2),
            "final_score": round(final_score, 2),
        }
        candidates.append(
            {
                "keyword": candidate["keyword"],
                "matched_alias": candidate["matched_alias"],
                "product_oid": candidate["product_oid"],
                "product_name": candidate["product_name"],
                "package_quantity": candidate["package_quantity"],
                "category_name": candidate["category_name"],
                "min_price_mop": candidate["min_price_mop"],
                "max_price_mop": candidate["max_price_mop"],
                "store_count": store_count,
                "sample_supermarkets": candidate["_sample_supermarkets"][:3],
                "score": ranking_factors["final_score"],
                "is_recommended": False,
                "recommendation_reason": "",
                "ranking_factors": ranking_factors,
                "match_score": ranking_factors["match_score"],
                "final_score": ranking_factors["final_score"],
                "forbidden_match": forbidden_match,
                "match_explanation": explain_match(keyword, candidate.get("product_name"), candidate.get("package_quantity"), candidate.get("category_name")),
            }
        )

    candidates = [item for item in candidates if not item.get("forbidden_match") or float(item["ranking_factors"]["final_score"]) > 0]
    candidates.sort(
        key=lambda item: (
            -float(item["ranking_factors"]["final_score"]),
            -int(item["store_count"]),
            float(item["min_price_mop"]),
            str(item.get("product_name") or ""),
        )
    )
    limited = candidates[: max(0, int(limit))]
    cheapest_price = min((float(item["min_price_mop"]) for item in limited), default=None)
    for index, candidate in enumerate(limited):
        candidate["is_recommended"] = index == 0
        candidate["recommendation_reason"] = _recommendation_reason(candidate, cheapest_price) if index == 0 else ""
    return limited


