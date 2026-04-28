from __future__ import annotations

import re
from typing import Any

KEYWORD_EXPANSIONS: dict[str, list[str]] = {
    "米": ["米", "白米", "香米", "珍珠米", "絲苗米", "泰國香米", "金象米", "青靈芝香米"],
    "麵": ["麵", "面", "公仔麵", "即食麵", "杯麵", "拉麵", "意粉", "通粉", "麵條"],
    "米粉": ["米粉"],
    "薯片": ["薯片", "potato chips", "chips", "樂事", "lay's", "lays", "pringles", "品客"],
    "薯條": ["薯條", "fries", "冷凍薯條"],
    "油": ["食油", "花生油", "粟米油", "芥花籽油", "橄欖油", "葵花籽油", "米糠油", "芥花油"],
    "糖": ["白砂糖", "砂糖", "冰糖", "黃糖", "片糖", "糖"],
    "紙巾": ["紙巾", "抽紙", "盒裝紙巾", "廁紙", "卷紙", "抹手紙", "衛生紙"],
    "\u6d17\u982d\u6c34": ["\u6d17\u982d\u6c34", "\u6d17\u9aee\u9732", "\u6d17\u9aee\u6c34", "\u6d17\u9aee\u4e73", "shampoo"],
    "牛奶": ["牛奶", "鮮奶", "全脂奶", "低脂奶", "脫脂奶"],
    "牙膏": ["牙膏", "toothpaste"],
    "洗衣液": ["洗衣液", "洗衣劑", "洗衣露", "洗衣粉"],
    "M&M": ["M&M", "m&m", "M and M", "M&M's", "朱古力豆", "巧克力豆"],
}
ALIASES = {"\u98df\u6cb9": "\u6cb9", "\u767d\u7c73": "\u7c73", "\u9762": "\u9eb5", "\u516c\u4ed4\u9eb5": "\u9eb5", "\u5373\u98df\u9eb5": "\u9eb5", "\u676f\u9eb5": "\u9eb5", "\u6d17\u9aee\u9732": "\u6d17\u982d\u6c34", "\u6d17\u9aee\u6c34": "\u6d17\u982d\u6c34", "\u6d17\u9aee\u4e73": "\u6d17\u982d\u6c34", "m&m": "M&M", "m and m": "M&M"}
NEGATIVE_TERMS: dict[str, list[str]] = {
    "米": ["米粉", "玉米", "粟米", "米餅", "米線", "米通", "糙米茶", "米漿", "米糊", "爆米花"],
    "麵": ["米粉", "河粉", "粉絲", "米線"],
    "米粉": ["白米", "香米", "珍珠米", "玉米", "粟米"],
    "薯片": ["薯條", "fries", "冷凍薯條"],
    "薯條": ["薯片", "chips", "pringles", "品客"],
    "油": ["護髮油", "洗髮油", "精油", "bb油", "嬰兒油", "油污", "清潔劑", "機油"],
    "糖": ["糖果", "朱古力", "巧克力", "口香糖", "糖水", "糖漿", "喉糖"],
    "紙巾": ["濕紙巾", "消毒濕紙巾", "濕巾", "萬用消毒"],
    "洗頭水": ["沐浴露", "洗手液", "護髮素", "潤髮乳", "護髮油"],
    "牛奶": ["奶粉", "煉奶", "椰奶", "豆奶", "奶茶", "乳酪"],
    "牙膏": ["牙刷", "漱口水", "牙線"],
    "洗衣液": ["洗潔精", "洗手液", "沐浴露"],
    "M&M": [],
}


def normalize_keyword(keyword: str) -> str:
    return str(keyword or "").strip().casefold()


def _canonical_keyword(keyword: str) -> str:
    text = str(keyword or "").strip()
    folded = text.casefold()
    if text in KEYWORD_EXPANSIONS:
        return text
    if folded in ALIASES:
        return ALIASES[folded]
    if text in ALIASES:
        return ALIASES[text]
    for canonical, terms in KEYWORD_EXPANSIONS.items():
        if folded in {normalize_keyword(t) for t in terms}:
            return canonical
    return text


def expand_keyword(keyword: str) -> list[str]:
    canonical = _canonical_keyword(keyword)
    terms = [canonical] + KEYWORD_EXPANSIONS.get(canonical, [str(keyword or "").strip()])
    seen: set[str] = set(); out: list[str] = []
    for term in terms:
        norm = normalize_keyword(term)
        if norm and norm not in seen:
            seen.add(norm); out.append(term)
    return out


def negative_terms_for_keyword(keyword: str) -> list[str]:
    return NEGATIVE_TERMS.get(_canonical_keyword(keyword), [])


def _contains(text: Any, term: str) -> bool:
    return normalize_keyword(term) in normalize_keyword(str(text or "")) if normalize_keyword(term) else False


def _has_any(text: Any, terms: list[str] | tuple[str, ...]) -> bool:
    return any(_contains(text, term) for term in terms)


def _parse_size(package_quantity: Any) -> tuple[float | None, str]:
    text = normalize_keyword(str(package_quantity or "")).replace(" ", "")
    m = re.search(r"(\d+(?:\.\d+)?)(?:kg|公斤|公斤)", text)
    if m: return float(m.group(1)), "kg"
    m = re.search(r"(\d+(?:\.\d+)?)(?:g|克)", text)
    if m: return float(m.group(1))/1000.0, "kg"
    m = re.search(r"(\d+(?:\.\d+)?)(?:ml|毫升)", text)
    if m: return float(m.group(1)), "ml"
    m = re.search(r"(\d+(?:\.\d+)?)(?:l|升)", text)
    if m: return float(m.group(1))*1000.0, "ml"
    return None, ""


def is_forbidden_match(keyword: str, product_name: Any, category_name: Any = "") -> bool:
    text = f"{product_name or ''} {category_name or ''}"
    return _has_any(text, negative_terms_for_keyword(keyword))


def package_preference_score(keyword: str, product_name: Any, package_quantity: Any = "") -> float:
    canonical = _canonical_keyword(keyword)
    name = str(product_name or "")
    size, unit = _parse_size(package_quantity)
    score = 0.0
    if canonical == "米":
        if _has_any(name, ["白米", "珍珠米", "香米", "絲苗米", "泰國香米", "金象米", "青靈芝香米"]): score += 12
        if unit == "kg" and size is not None:
            if 4 <= size <= 10 or size == 25: score += 10
            elif size < 1: score -= 5
    elif canonical == "洗頭水":
        if unit == "ml" and size and 300 <= size <= 1200: score += 5
    elif canonical in {"油", "牛奶"}:
        if unit == "ml" and size and size >= 500: score += 3
    return score


def candidate_text_match_score(keyword: str, product_name: Any, package_quantity: Any = "", category_name: Any = "") -> float:
    product = str(product_name or "")
    category = str(category_name or "")
    text = f"{product} {category}"
    score = 0.0
    canonical = _canonical_keyword(keyword)
    for term in expand_keyword(canonical):
        if _contains(product, term): score += 10 if normalize_keyword(term) == normalize_keyword(canonical) else 7
        if _contains(category, term): score += 4
    score += package_preference_score(canonical, product, package_quantity)
    for term in negative_terms_for_keyword(canonical):
        if _contains(product, term): score -= 50
        elif _contains(category, term): score -= 20
    if is_forbidden_match(canonical, product, category):
        score -= 100
    return score


def explain_match(keyword: str, product_name: Any, package_quantity: Any = "", category_name: Any = "") -> dict[str, Any]:
    canonical = _canonical_keyword(keyword)
    forbidden = is_forbidden_match(canonical, product_name, category_name)
    return {
        "keyword": keyword,
        "canonical_keyword": canonical,
        "expanded_terms": expand_keyword(canonical),
        "negative_terms": negative_terms_for_keyword(canonical),
        "forbidden_match": forbidden,
        "match_score": round(candidate_text_match_score(canonical, product_name, package_quantity, category_name), 2),
    }
