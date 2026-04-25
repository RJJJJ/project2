from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from services.product_aliases import load_aliases


CHINESE_DIGITS = {
    "零": 0,
    "一": 1,
    "二": 2,
    "兩": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}
QUANTITY_PATTERN = re.compile(r"([0-9]+|[一二兩两三四五六七八九十]+)\s*[包支個个盒瓶袋條条件罐]*\s*$")
SEPARATOR_PATTERN = re.compile(r"[，,、。；;\s]|和|及|與|与|跟|買|买|要|想")


@dataclass(frozen=True)
class ProductMatch:
    start: int
    end: int
    keyword: str


def _parse_chinese_number(value: str) -> int | None:
    if not value:
        return None
    if value == "十":
        return 10
    if "十" in value:
        left, _, right = value.partition("十")
        tens = CHINESE_DIGITS.get(left, 1) if left else 1
        ones = CHINESE_DIGITS.get(right, 0) if right else 0
        return tens * 10 + ones
    if len(value) == 1:
        return CHINESE_DIGITS.get(value)
    return None


def _parse_quantity(value: str) -> int | None:
    if value.isdigit():
        quantity = int(value)
        return quantity if quantity > 0 else None
    return _parse_chinese_number(value)


def _context_start(text: str, product_start: int) -> int:
    last_separator_end = 0
    for match in SEPARATOR_PATTERN.finditer(text[:product_start]):
        last_separator_end = match.end()
    return last_separator_end


def _quantity_before(text: str, product_start: int) -> int:
    context = text[_context_start(text, product_start):product_start]
    match = QUANTITY_PATTERN.search(context)
    if not match:
        return 1
    return _parse_quantity(match.group(1)) or 1


def _find_product_matches(text: str, keywords: list[str]) -> list[ProductMatch]:
    matches: list[ProductMatch] = []
    occupied: list[range] = []
    for keyword in sorted(keywords, key=len, reverse=True):
        if not keyword:
            continue
        for match in re.finditer(re.escape(keyword), text):
            current = range(match.start(), match.end())
            if any(match.start() < item.stop and match.end() > item.start for item in occupied):
                continue
            occupied.append(current)
            matches.append(ProductMatch(match.start(), match.end(), keyword))
    return sorted(matches, key=lambda item: item.start)


def parse_shopping_text(text: str) -> list[dict[str, Any]]:
    aliases = load_aliases()
    keywords = list(aliases.keys())
    normalized = text.strip()
    if not normalized:
        return []

    items: list[dict[str, Any]] = []
    for match in _find_product_matches(normalized, keywords):
        items.append(
            {
                "keyword": match.keyword,
                "quantity": _quantity_before(normalized, match.start),
            }
        )
    return items
