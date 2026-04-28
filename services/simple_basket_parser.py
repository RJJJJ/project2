from __future__ import annotations

import re
from typing import Any

CHINESE_NUMBERS = {
    "\u4e00": 1,
    "\u5169": 2,
    "\u4e8c": 2,
    "\u4e09": 3,
}
UNIT_CHARS = "\u5305\u652f\u76d2\u500b\u5377\u6a3d\u74f6\u888b"
DEFAULT_KEYWORDS = ["\u6d17\u982d\u6c34", "\u6d17\u9aee\u9732", "\u6d17\u9aee\u6c34", "\u7d19\u5dfe", "\u725b\u5976", "\u6d17\u8863\u6db2", "\u7259\u818f", "\u98df\u6cb9", "\u7c73"]
KEYWORD_CANONICAL = {
    "\u6d17\u9aee\u9732": "\u6d17\u982d\u6c34",
    "\u6d17\u9aee\u6c34": "\u6d17\u982d\u6c34",
}
SEPARATOR_RE = re.compile(r"[，,、；;。\n]+")
LOCATION_RE = re.compile(r"(?:\u6211)?(?:\u5728|\u55ba)([^，,、。\s]+)")


def _quantity_from_prefix(prefix: str) -> tuple[int, str | None]:
    match = re.search(rf"([0-9]+|[\u4e00\u5169\u4e8c\u4e09])\s*([{UNIT_CHARS}]?)\s*$", prefix)
    if not match:
        return 1, None
    raw = match.group(1)
    quantity = int(raw) if raw.isdigit() else CHINESE_NUMBERS.get(raw, 1)
    return quantity, match.group(2) or None


def canonical_keyword(keyword: str) -> str:
    return KEYWORD_CANONICAL.get(keyword, keyword)


def extract_location_text(text: str) -> str | None:
    match = LOCATION_RE.search(text or "")
    return match.group(1).strip() if match else None


def parse_simple_basket_text(text: str) -> list[dict[str, Any]]:
    normalized = str(text or "").strip()
    if not normalized:
        return []
    matches: list[tuple[int, int, str]] = []
    occupied: list[range] = []
    for keyword in sorted(DEFAULT_KEYWORDS, key=len, reverse=True):
        for match in re.finditer(re.escape(keyword), normalized, flags=re.IGNORECASE):
            current = range(match.start(), match.end())
            if any(match.start() < item.stop and match.end() > item.start for item in occupied):
                continue
            occupied.append(current)
            matches.append((match.start(), match.end(), canonical_keyword(keyword)))
    matches.sort(key=lambda item: item[0])
    items: list[dict[str, Any]] = []
    for start, end, keyword in matches:
        prefix_start = 0
        separators = list(SEPARATOR_RE.finditer(normalized[:start]))
        if separators:
            prefix_start = separators[-1].end()
        quantity, unit = _quantity_from_prefix(normalized[prefix_start:start])
        item: dict[str, Any] = {"keyword": keyword, "quantity": quantity}
        if unit:
            item["unit"] = unit
        item["raw_text"] = normalized[prefix_start:end].strip()
        items.append(item)
    return items
