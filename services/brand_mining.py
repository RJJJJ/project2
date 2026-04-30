from __future__ import annotations

import re
from typing import Any

from services.product_direct_search import BRAND_TERMS, normalize_product_name_for_lookup


GENERIC_BRAND_STOPWORDS = {
    "即食麵",
    "即食面",
    "砂糖",
    "牛奶",
    "豆奶",
    "洗髮乳",
    "洗頭水",
    "薯片",
    "紙巾",
    "濕紙巾",
    "食油",
    "飲品",
    "朱古力",
    "牙膏",
    "沐浴露",
    "餅乾",
    "咖啡",
    "茶",
}
PRODUCT_TYPE_MARKERS = sorted(GENERIC_BRAND_STOPWORDS | {"麻油味", "原味", "低糖", "純正"}, key=len, reverse=True)


def _clean_brand(value: str) -> str:
    text = str(value or "").strip(" -_　()（）[]【】,，。.")
    for marker in PRODUCT_TYPE_MARKERS:
        if text == marker:
            return ""
    if not text or len(normalize_product_name_for_lookup(text)) < 2:
        return ""
    if normalize_product_name_for_lookup(text) in {normalize_product_name_for_lookup(v) for v in GENERIC_BRAND_STOPWORDS}:
        return ""
    return text


def _leading_chunks(product_name: str) -> list[str]:
    name = str(product_name or "").strip()
    chunks: list[str] = []
    for seed in BRAND_TERMS:
        if seed and seed in name:
            chunks.append(seed)
    english = re.match(r"^([A-Za-z][A-Za-z0-9&'.-]{1,20})", name)
    if english:
        chunks.append(english.group(1))
    chinese = re.match(r"^([\u4e00-\u9fffA-Za-z0-9&'.-]{2,8})", name)
    if chinese:
        head = chinese.group(1)
        cut_positions = [head.find(marker) for marker in PRODUCT_TYPE_MARKERS if marker in head]
        cut_positions = [pos for pos in cut_positions if pos > 0]
        if cut_positions:
            head = head[: min(cut_positions)]
        # Prefer short known-like prefixes before flavor/category words.
        for marker in PRODUCT_TYPE_MARKERS:
            pos = name.find(marker)
            if 1 < pos <= 6:
                head = name[:pos]
                break
        chunks.append(head)
    return [clean for chunk in chunks if (clean := _clean_brand(chunk))]


def extract_brand_candidates_from_products(products: list[dict]) -> list[dict]:
    stats: dict[str, dict[str, Any]] = {}
    for product in products:
        name = str(product.get("product_name") or "")
        for brand in _leading_chunks(name):
            norm = normalize_product_name_for_lookup(brand)
            if not norm:
                continue
            entry = stats.setdefault(
                norm,
                {
                    "brand": brand,
                    "aliases": set(),
                    "product_count": 0,
                    "example_products": [],
                    "confidence": 0.0,
                },
            )
            entry["aliases"].add(brand)
            entry["product_count"] += 1
            if len(entry["example_products"]) < 5:
                entry["example_products"].append(name)
    results: list[dict[str, Any]] = []
    for norm, entry in stats.items():
        count = int(entry["product_count"])
        seed_bonus = 0.25 if any(normalize_product_name_for_lookup(seed) == norm for seed in BRAND_TERMS) else 0.0
        confidence = min(0.99, 0.45 + min(count, 10) * 0.05 + seed_bonus)
        if count < 1 and confidence < 0.6:
            continue
        results.append(
            {
                "brand": entry["brand"],
                "normalized": norm,
                "aliases": sorted(entry["aliases"]),
                "product_count": count,
                "confidence": round(confidence, 3),
                "example_products": entry["example_products"],
            }
        )
    results.sort(key=lambda item: (-float(item["confidence"]), -int(item["product_count"]), str(item["brand"])))
    return results


def build_brand_alias_index(products: list[dict]) -> dict:
    brands = extract_brand_candidates_from_products(products)
    aliases: dict[str, dict[str, Any]] = {}
    for item in brands:
        for alias in item.get("aliases") or [item.get("brand")]:
            norm = normalize_product_name_for_lookup(alias)
            if norm:
                aliases[norm] = {**item, "matched_alias": alias}
    for seed in BRAND_TERMS:
        norm = normalize_product_name_for_lookup(seed)
        if norm and norm not in aliases:
            aliases[norm] = {"brand": seed, "normalized": norm, "aliases": [seed], "product_count": 0, "confidence": 0.75, "example_products": [], "matched_alias": seed}
    return {"brands": brands, "aliases": aliases}


def detect_brand_query(query: str, brand_index: dict) -> dict:
    normalized = normalize_product_name_for_lookup(query)
    aliases = brand_index.get("aliases") or {}
    if not normalized:
        return {"matched": False, "brand": None, "confidence": "low", "score": 0.0, "reason": "empty query"}
    best: dict[str, Any] | None = None
    for alias_norm, item in aliases.items():
        if not alias_norm:
            continue
        score = 0.0
        if normalized == alias_norm:
            score = 1.0
        elif alias_norm in normalized:
            score = 0.85
        elif normalized in alias_norm and len(normalized) >= 3:
            score = 0.72
        if score <= 0:
            continue
        candidate = {**item, "score": round(score * float(item.get("confidence") or 0.5), 3)}
        if best is None or candidate["score"] > best["score"]:
            best = candidate
    if not best:
        return {"matched": False, "brand": None, "confidence": "low", "score": 0.0, "reason": "no brand alias matched"}
    confidence = "high" if best["score"] >= 0.75 else "medium"
    return {"matched": True, "brand": best.get("brand"), "matched_alias": best.get("matched_alias"), "confidence": confidence, "score": best["score"], "reason": "catalog brand alias matched"}
