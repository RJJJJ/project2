from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import re
import unicodedata

from services.product_catalog_loader import load_products_from_sqlite

DEFAULT_HIGH_RISK_TERMS = [
    "糖",
    "油",
    "米",
    "麵",
    "面",
    "奶",
    "水",
    "蛋",
    "雞蛋",
    "紙",
    "紙巾",
    "朱古力",
    "飲品",
    "茶",
    "咖啡",
    "鹽",
    "醬",
    "粉",
]

GENERIC_AMBIGUOUS_TERMS = {"糖", "油", "米", "麵", "面", "奶", "水", "紙", "紙巾", "朱古力", "飲品", "茶", "咖啡", "鹽", "醬", "粉"}
NOT_COVERED_GENERIC_TERMS = {"蛋", "雞蛋"}

TERM_ALIASES = {
    "糖": "sugar",
    "油": "oil",
    "米": "rice",
    "麵": "noodle",
    "面": "noodle_simplified",
    "奶": "milk",
    "水": "water",
    "蛋": "egg",
    "雞蛋": "chicken_egg",
    "紙": "paper",
    "紙巾": "tissue",
    "朱古力": "chocolate",
    "飲品": "drink",
    "茶": "tea",
    "咖啡": "coffee",
    "鹽": "salt",
    "醬": "sauce",
    "粉": "powder",
}


def load_catalog_for_confusion_audit(db_path: str | Path) -> list[dict]:
    return load_products_from_sqlite(db_path)


def _normalize_text(value: Any) -> str:
    return unicodedata.normalize("NFKC", str(value or "")).strip()


def _contains_any(text: str, needles: list[str] | tuple[str, ...] | set[str]) -> str | None:
    for needle in needles:
        if needle and needle in text:
            return needle
    return None


def _matched_context(text: str, term: str, radius: int = 6) -> str:
    index = text.find(term)
    if index < 0:
        return term
    start = max(0, index - radius)
    end = min(len(text), index + len(term) + radius)
    return text[start:end]


def _category_label(product: dict[str, Any]) -> str:
    category_name = _normalize_text(product.get("category_name"))
    category_id = product.get("category_id")
    if category_name:
        return category_name
    if category_id in (None, ""):
        return ""
    return f"category_{category_id}"


def _base_occurrence(term: str, product: dict[str, Any]) -> dict[str, Any]:
    product_name = _normalize_text(product.get("product_name"))
    return {
        "term": term,
        "product_oid": product.get("product_oid"),
        "product_name": product_name,
        "category_id": product.get("category_id"),
        "category_name": _category_label(product),
        "package_quantity": _normalize_text(product.get("package_quantity")),
        "occurrence_type": "needs_review",
        "risk_level": "high",
        "reason": f"'{term}' appears in product name but no deterministic rule matched.",
        "suggested_guardrail": "review",
        "matched_context": _matched_context(product_name, term),
    }


def _classification(
    base: dict[str, Any],
    occurrence_type: str,
    risk_level: str,
    reason: str,
    suggested_guardrail: str,
) -> dict[str, Any]:
    item = dict(base)
    item.update(
        {
            "occurrence_type": occurrence_type,
            "risk_level": risk_level,
            "reason": reason,
            "suggested_guardrail": suggested_guardrail,
        }
    )
    return item


def _classify_sugar(base: dict[str, Any], name: str) -> dict[str, Any]:
    if marker := _contains_any(name, ["低糖", "無糖", "少糖", "微糖"]):
        return _classification(base, "attribute_only", "high", f"'{marker}' is a sweetness attribute, not cooking sugar.", "exclude")
    if marker := _contains_any(name, ["薄荷糖", "香口珠", "喉糖", "潤喉糖", "糖果", "軟糖", "硬糖"]):
        return _classification(base, "different_category", "high", f"'{marker}' is candy / confectionery rather than cooking sugar.", "exclude")
    if marker := _contains_any(name, ["蜜糖", "糖漿", "朱古力糖"]):
        return _classification(base, "needs_review", "medium", f"'{marker}' may be related but should be manually reviewed.", "review")
    if marker := _contains_any(name, ["白砂糖", "砂糖", "冰糖", "黃糖", "片糖", "赤砂糖", "方糖"]):
        return _classification(base, "true_product", "low", f"'{marker}' is a primary sugar product.", "allow")
    return _classification(base, "ambiguous", "medium", "Sugar-related naming is unclear without stronger catalog evidence.", "clarify")


def _classify_oil(base: dict[str, Any], name: str) -> dict[str, Any]:
    if marker := _contains_any(name, ["麻油味", "黑蒜油味", "辣油味", "蒜油味", "油味"]):
        return _classification(base, "flavor_only", "high", f"'{marker}' is a flavor marker, not cooking oil.", "exclude")
    if "沙律油" in name:
        return _classification(base, "needs_review", "medium", "Salad oil may be edible oil but should be verified against taxonomy.", "review")
    if marker := _contains_any(name, ["蠔油", "醬油", "麻油", "油浸", "油咖喱", "魚油", "潤膚油", "護髮油", "精油", "香薰油"]):
        return _classification(base, "different_category", "high", f"'{marker}' belongs to sauce, preserved food, supplement, or personal care.", "exclude")
    if marker := _contains_any(name, ["花生油", "粟米油", "芥花籽油", "橄欖油", "調和油", "食油", "生油", "稻米油", "米糠油"]):
        guardrail = "allow" if marker != "米糠油" else "allow"
        return _classification(base, "true_product", "low", f"'{marker}' is a cooking oil product.", guardrail)
    return _classification(base, "ambiguous", "medium", "Oil-related naming is broad and may require clarification.", "clarify")


def _classify_egg(base: dict[str, Any], name: str, term: str) -> dict[str, Any]:
    if marker := _contains_any(name, ["雞蛋幼面", "全蛋麵", "全蛋面", "蛋黃醬", "蛋卷", "蛋糕", "蛋撻", "蛋麵", "蛋面"]):
        return _classification(base, "product_type_modifier", "high", f"'{marker}' contains egg wording as part of another product type.", "exclude")
    if marker := _contains_any(name, ["皮蛋", "鹹蛋", "鵪鶉蛋", "蛋白", "蛋黃"]):
        return _classification(base, "needs_review", "medium", f"'{marker}' is egg-related but may not match the current monitored egg intent safely.", "review")
    egg_only_pattern = re.compile(r"(鮮蛋|雞蛋)(?!幼面|幼麵|麵|面|卷|糕|醬)")
    if egg_only_pattern.search(name):
        return _classification(base, "true_product", "medium", f"'{term}' appears to refer to an actual egg product.", "allow")
    if name == term:
        return _classification(base, "ambiguous", "high", "Bare egg wording requires coverage verification.", "not_covered")
    return _classification(base, "needs_review", "high", "Egg wording is present but the catalog meaning is not reliable enough.", "review")


def _classify_rice(base: dict[str, Any], name: str) -> dict[str, Any]:
    if marker := _contains_any(name, ["米粉", "米線", "排粉", "米糠油", "稻米油", "米漿", "米餅", "玉米", "蝦米", "意米"]):
        return _classification(base, "different_category", "high", f"'{marker}' is not a primary rice grain product.", "exclude")
    if marker := _contains_any(name, ["香米", "珍珠米", "絲苗米", "丝苗米", "糙米", "糯米", "茉莉香米", "白米", "日本米", "泰國香米"]):
        return _classification(base, "true_product", "medium", f"'{marker}' is a rice grain product.", "clarify")
    return _classification(base, "ambiguous", "medium", "Rice wording is broad and may refer to grain or another rice-derived product.", "clarify")


def _classify_noodle(base: dict[str, Any], name: str) -> dict[str, Any]:
    if marker := _contains_any(name, ["即食麵", "杯麵", "碗麵", "公仔麵", "全蛋麵", "全蛋面", "幼面", "幼麵", "意大利麵", "意大利面", "意粉", "通心粉", "上海麵", "拉麵", "拉面", "蝦子麵", "蝦子面"]):
        return _classification(base, "true_product", "medium", f"'{marker}' is a noodle / pasta product, but the generic query is still broad.", "clarify")
    if marker := _contains_any(name, ["麵包", "面包", "面霜", "麵豉", "麵鼓"]):
        return _classification(base, "different_category", "high", f"'{marker}' is not a noodle product.", "exclude")
    return _classification(base, "ambiguous", "medium", "Noodle wording is product-like but still too broad for auto-resolution.", "clarify")


def _classify_milk(base: dict[str, Any], name: str) -> dict[str, Any]:
    if marker := _contains_any(name, ["豆奶", "豆乳", "奶茶", "奶粉", "煉奶", "乳酪", "奶昔"]):
        return _classification(base, "ambiguous", "high", f"'{marker}' is a milk-adjacent subtype that should not be auto-mapped from generic 奶.", "clarify")
    if marker := _contains_any(name, ["牛奶", "鮮奶", "全脂奶", "低脂奶", "脫脂奶"]):
        return _classification(base, "true_product", "medium", f"'{marker}' is a milk product, but generic 奶 is still ambiguous.", "clarify")
    return _classification(base, "ambiguous", "medium", "Milk wording is broad across dairy and non-dairy products.", "clarify")


def _classify_water(base: dict[str, Any], name: str) -> dict[str, Any]:
    if marker := _contains_any(name, ["洗髮水", "漱口水", "消毒水", "香水", "花露水", "潔廁水", "漂白水", "洗衣水"]):
        return _classification(base, "different_category", "high", f"'{marker}' is a non-drinking liquid product.", "exclude")
    if marker := _contains_any(name, ["礦泉水", "飲用水", "蒸餾水", "純淨水", "梳打水", "氣泡水"]):
        return _classification(base, "true_product", "medium", f"'{marker}' is a drinking-water product, but generic 水 is ambiguous.", "clarify")
    return _classification(base, "ambiguous", "high", "Water wording spans beverage and non-beverage categories.", "clarify")


def _classify_paper(base: dict[str, Any], name: str, term: str) -> dict[str, Any]:
    if marker := _contains_any(name, ["濕紙巾", "消毒濕紙巾", "消毒濕巾", "濕廁紙", "紙尿片"]):
        return _classification(base, "different_category", "high", f"'{marker}' is a different hygiene subtype from dry tissue.", "exclude")
    if marker := _contains_any(name, ["紙巾", "衛生紙", "卷紙", "面紙", "紙手巾", "盒裝紙巾", "抽取式紙巾"]):
        guardrail = "clarify" if term in {"紙", "紙巾"} else "allow"
        return _classification(base, "true_product", "medium", f"'{marker}' is a tissue / paper product.", guardrail)
    return _classification(base, "ambiguous", "high", "Paper wording is broad across tissue and non-tissue products.", "clarify")


def _classify_chocolate(base: dict[str, Any], name: str) -> dict[str, Any]:
    if marker := _contains_any(name, ["朱古力飲品", "朱古力牛奶飲品", "可可飲品", "朱古力奶"]):
        return _classification(base, "ambiguous", "high", f"'{marker}' is a chocolate drink subtype that needs clarification.", "clarify")
    if marker := _contains_any(name, ["朱古力醬", "榛子可可醬"]):
        return _classification(base, "ambiguous", "high", f"'{marker}' is a spread / sauce subtype, not generic chocolate.", "clarify")
    if marker := _contains_any(name, ["朱古力熊仔餅", "朱古力餅", "朱古力糖", "朱古力"]):
        return _classification(base, "true_product", "medium", f"'{marker}' is chocolate-related, but generic 朱古力 spans multiple subtypes.", "clarify")
    return _classification(base, "needs_review", "medium", "Chocolate wording needs manual subtype confirmation.", "review")


def _classify_drink(base: dict[str, Any], name: str) -> dict[str, Any]:
    if marker := _contains_any(name, ["飲品", "汽水", "可樂", "豆奶", "牛奶飲品", "茶飲", "咖啡飲品"]):
        return _classification(base, "true_product", "medium", f"'{marker}' is a drink product class, but generic 飲品 is too broad.", "clarify")
    return _classification(base, "ambiguous", "high", "Drink wording is catalog-wide and requires subtype clarification.", "clarify")


def _classify_tea(base: dict[str, Any], name: str) -> dict[str, Any]:
    if marker := _contains_any(name, ["奶茶", "檸檬茶", "綠茶", "紅茶", "烏龍茶", "花茶", "茶飲"]):
        return _classification(base, "true_product", "medium", f"'{marker}' is tea-related, but generic 茶 is broad.", "clarify")
    if marker := _contains_any(name, ["茶樹油"]):
        return _classification(base, "different_category", "high", f"'{marker}' is not a tea beverage / grocery tea product.", "exclude")
    return _classification(base, "ambiguous", "medium", "Tea wording is too broad for single-intent resolution.", "clarify")


def _classify_coffee(base: dict[str, Any], name: str) -> dict[str, Any]:
    if marker := _contains_any(name, ["咖啡粉", "咖啡豆", "即溶咖啡", "樽裝咖啡", "咖啡飲品", "咖啡"]):
        return _classification(base, "true_product", "medium", f"'{marker}' is coffee-related, but generic 咖啡 spans multiple product forms.", "clarify")
    return _classification(base, "ambiguous", "medium", "Coffee wording is broad across powder, beans, and ready-to-drink products.", "clarify")


def _classify_salt(base: dict[str, Any], name: str) -> dict[str, Any]:
    if marker := _contains_any(name, ["鹽味", "鹽焗"]):
        return _classification(base, "flavor_only", "high", f"'{marker}' is a flavor marker, not table salt.", "exclude")
    if marker := _contains_any(name, ["食鹽", "海鹽", "幼鹽", "岩鹽", "粗鹽"]):
        return _classification(base, "true_product", "medium", f"'{marker}' is a salt product.", "clarify")
    return _classification(base, "ambiguous", "medium", "Salt wording needs subtype verification.", "clarify")


def _classify_sauce(base: dict[str, Any], name: str) -> dict[str, Any]:
    if marker := _contains_any(name, ["辣椒醬", "番茄醬", "沙律醬", "花生醬", "芝麻醬", "醬油", "蠔油"]):
        return _classification(base, "true_product", "medium", f"'{marker}' is a sauce product, but generic 醬 is broad.", "clarify")
    return _classification(base, "ambiguous", "high", "Sauce wording spans many incompatible subtypes.", "clarify")


def _classify_powder(base: dict[str, Any], name: str) -> dict[str, Any]:
    if marker := _contains_any(name, ["意粉", "粉絲", "河粉", "米粉"]):
        return _classification(base, "different_category", "high", f"'{marker}' is a noodle / starch product, not generic powder.", "exclude")
    if marker := _contains_any(name, ["奶粉", "洗衣粉", "咖啡粉", "調味粉", "蛋白粉", "麵粉"]):
        return _classification(base, "ambiguous", "high", f"'{marker}' is a specific powder subtype; generic 粉 should not auto-resolve.", "clarify")
    return _classification(base, "ambiguous", "medium", "Powder wording spans unrelated categories.", "clarify")


def _generic_classify(base: dict[str, Any], term: str, name: str) -> dict[str, Any]:
    if term in GENERIC_AMBIGUOUS_TERMS:
        return _classification(base, "ambiguous", "medium", f"'{term}' is a broad high-risk term.", "clarify")
    if term in NOT_COVERED_GENERIC_TERMS:
        return _classification(base, "ambiguous", "high", f"'{term}' currently needs coverage verification.", "not_covered")
    return _classification(base, "needs_review", "high", "No generic rule matched.", "review")


def classify_term_occurrence(term: str, product: dict, config: dict | None = None) -> dict:
    del config  # reserved for future rule overrides
    base = _base_occurrence(term, product)
    name = _normalize_text(product.get("product_name"))
    if not name or term not in name:
        return base
    if term == "糖":
        return _classify_sugar(base, name)
    if term == "油":
        return _classify_oil(base, name)
    if term in {"蛋", "雞蛋"}:
        return _classify_egg(base, name, term)
    if term == "米":
        return _classify_rice(base, name)
    if term in {"麵", "面"}:
        return _classify_noodle(base, name)
    if term == "奶":
        return _classify_milk(base, name)
    if term == "水":
        return _classify_water(base, name)
    if term in {"紙", "紙巾"}:
        return _classify_paper(base, name, term)
    if term == "朱古力":
        return _classify_chocolate(base, name)
    if term == "飲品":
        return _classify_drink(base, name)
    if term == "茶":
        return _classify_tea(base, name)
    if term == "咖啡":
        return _classify_coffee(base, name)
    if term == "鹽":
        return _classify_salt(base, name)
    if term == "醬":
        return _classify_sauce(base, name)
    if term == "粉":
        return _classify_powder(base, name)
    return _generic_classify(base, term, name)


def audit_confusion_terms(
    products: list[dict],
    terms: list[str] | None = None,
    config: dict | None = None,
) -> dict:
    selected_terms = list(dict.fromkeys(terms or DEFAULT_HIGH_RISK_TERMS))
    occurrences: list[dict[str, Any]] = []
    per_term: dict[str, dict[str, Any]] = {}
    for term in selected_terms:
        term_occurrences: list[dict[str, Any]] = []
        for product in products:
            name = _normalize_text(product.get("product_name"))
            if not name or term not in name:
                continue
            item = classify_term_occurrence(term, product, config=config)
            term_occurrences.append(item)
            occurrences.append(item)
        by_type = Counter(item["occurrence_type"] for item in term_occurrences)
        by_risk = Counter(item["risk_level"] for item in term_occurrences)
        by_guardrail = Counter(item["suggested_guardrail"] for item in term_occurrences)
        high_risk_products = [
            {
                "product_oid": item.get("product_oid"),
                "product_name": item.get("product_name"),
                "occurrence_type": item.get("occurrence_type"),
                "reason": item.get("reason"),
                "suggested_guardrail": item.get("suggested_guardrail"),
            }
            for item in term_occurrences
            if item.get("risk_level") == "high"
        ]
        manual_review_products = [
            {
                "product_oid": item.get("product_oid"),
                "product_name": item.get("product_name"),
                "occurrence_type": item.get("occurrence_type"),
                "reason": item.get("reason"),
            }
            for item in term_occurrences
            if item.get("suggested_guardrail") == "review" or item.get("occurrence_type") == "needs_review"
        ]
        per_term[term] = {
            "total_occurrences": len(term_occurrences),
            "by_occurrence_type": dict(by_type),
            "by_risk_level": dict(by_risk),
            "suggested_guardrails": dict(by_guardrail),
            "high_risk_products": high_risk_products,
            "manual_review_products": manual_review_products,
        }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "products_total": len(products),
        "terms": per_term,
        "occurrences": occurrences,
    }


def build_confusion_summary(audit_result: dict) -> dict:
    terms = audit_result.get("terms") or {}
    scored_terms: list[dict[str, Any]] = []
    high_risk_occurrence_count = 0
    manual_review_count = 0
    for term, info in terms.items():
        high_count = int((info.get("by_risk_level") or {}).get("high", 0))
        medium_count = int((info.get("by_risk_level") or {}).get("medium", 0))
        review_count = len(info.get("manual_review_products") or [])
        high_risk_occurrence_count += high_count
        manual_review_count += review_count
        scored_terms.append(
            {
                "term": term,
                "total_occurrences": int(info.get("total_occurrences") or 0),
                "high_risk_count": high_count,
                "manual_review_count": review_count,
                "risk_score": (high_count * 3) + (medium_count * 2) + review_count,
            }
        )
    scored_terms.sort(key=lambda item: (-item["risk_score"], -item["high_risk_count"], -item["total_occurrences"], item["term"]))
    terms_needing_manual_review = [item["term"] for item in scored_terms if item["manual_review_count"] > 0]
    return {
        "generated_at": audit_result.get("generated_at"),
        "products_total": int(audit_result.get("products_total") or 0),
        "terms_total": len(terms),
        "top_risky_terms": scored_terms[:10],
        "high_risk_occurrence_count": high_risk_occurrence_count,
        "manual_review_count": manual_review_count,
        "terms_needing_manual_review": terms_needing_manual_review,
    }


def _slug(term: str) -> str:
    return TERM_ALIASES.get(term, re.sub(r"[^a-z0-9]+", "_", _normalize_text(term).encode("ascii", "ignore").decode("ascii").lower()).strip("_") or "term")


def _is_strict_direct_case(product_name: str, occurrence_type: str) -> bool:
    if occurrence_type not in {"product_type_modifier", "flavor_only"}:
        return False
    if len(product_name) < 4 or len(product_name) > 14:
        return False
    if re.search(r"[\s\-–—()（）\[\]{}<>/\\,:：;；·]", product_name):
        return False
    return True


def _build_generic_term_case(term: str, high_risk_names: list[str], strict: bool) -> dict[str, Any]:
    expected: dict[str, Any]
    if term in NOT_COVERED_GENERIC_TERMS:
        expected = {
            "status": "not_covered",
            "query_type": "not_covered_request",
            "must_not_include_product_names": high_risk_names,
        }
    else:
        expected = {
            "status_in": ["needs_clarification", "ambiguous"],
            "must_not_include_product_names": high_risk_names,
        }
    return {
        "case_id": f"confusion_{_slug(term)}_generic_001",
        "term": term,
        "query": term,
        "expected": expected,
        "source": "catalog_confusion_audit",
        "needs_manual_label": not strict,
        "case_type": "generic_term_guardrail",
    }


def _build_direct_product_case(term: str, occurrence: dict[str, Any], index: int) -> dict[str, Any]:
    product_name = str(occurrence.get("product_name") or "")
    strict = _is_strict_direct_case(product_name, str(occurrence.get("occurrence_type") or ""))
    expected: dict[str, Any] = {
        "not_status": ["not_covered"],
        "must_include_product_names": [product_name],
    }
    if strict:
        expected["query_type_in"] = ["direct_product_search", "partial_product_search"]
    return {
        "case_id": f"confusion_{_slug(term)}_direct_{index:03d}",
        "term": term,
        "query": product_name,
        "expected": expected,
        "source": "catalog_confusion_audit",
        "needs_manual_label": not strict,
        "case_type": "exact_product_guardrail",
        "from_product_oid": occurrence.get("product_oid"),
    }


def generate_adversarial_cases_from_audit(
    audit_result: dict,
    max_cases_per_term: int = 10,
) -> list[dict]:
    occurrences = audit_result.get("occurrences") or []
    by_term: dict[str, list[dict[str, Any]]] = {}
    for item in occurrences:
        by_term.setdefault(str(item.get("term") or ""), []).append(item)
    cases: list[dict[str, Any]] = []
    for term, term_occurrences in by_term.items():
        if not term:
            continue
        high_risk_exclusions = [
            str(item.get("product_name") or "")
            for item in term_occurrences
            if item.get("suggested_guardrail") == "exclude" and item.get("risk_level") == "high"
        ]
        high_risk_exclusions = list(dict.fromkeys([name for name in high_risk_exclusions if name]))[: max(0, int(max_cases_per_term))]
        strict_generic = bool(high_risk_exclusions) and term in (GENERIC_AMBIGUOUS_TERMS | NOT_COVERED_GENERIC_TERMS)
        if high_risk_exclusions or term in NOT_COVERED_GENERIC_TERMS:
            cases.append(_build_generic_term_case(term, high_risk_exclusions[:3], strict_generic))
        direct_candidates = [
            item
            for item in term_occurrences
            if item.get("occurrence_type") in {"flavor_only", "product_type_modifier", "different_category", "ambiguous"}
            and item.get("product_name")
            and len(str(item.get("product_name"))) >= 4
        ]
        seen_products: set[str] = set()
        generated = 0
        for occurrence in direct_candidates:
            product_name = str(occurrence.get("product_name") or "")
            if product_name in seen_products:
                continue
            seen_products.add(product_name)
            cases.append(_build_direct_product_case(term, occurrence, generated + 1))
            generated += 1
            if generated >= max(1, min(3, max_cases_per_term - 1)):
                break
        if not strict_generic and term in {"糖", "油", "雞蛋"} and not any(case["term"] == term and case["case_type"] == "generic_term_guardrail" for case in cases):
            cases.append(_build_generic_term_case(term, high_risk_exclusions[:3], False))
    return cases
