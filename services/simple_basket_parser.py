from __future__ import annotations

import re
from typing import Any

CHINESE_NUMBERS = {"一": 1, "二": 2, "兩": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
UNIT_WORDS = ("包", "支", "枝", "盒", "個", "瓶", "樽", "袋", "罐", "條", "卷", "排", "打")
UNIT_RE = "|".join(map(re.escape, UNIT_WORDS))
KNOWN_KEYWORDS = [
    "洗頭水", "洗髮露", "洗髮水", "洗衣液", "可口可樂", "Coca Cola", "M and M", "m and m",
    "M&M", "m&m", "C&S", "KitKat", "Tempo", "OREO", "Oreo", "薯條", "薯片", "米粉", "紙巾",
    "牛奶", "牙膏", "食油", "白米", "麵", "面", "油", "糖", "米",
]
KEYWORD_CANONICAL = {"洗髮露": "洗頭水", "洗髮水": "洗頭水", "面": "麵", "食油": "油", "白米": "米", "m&m": "M&M", "M and M": "M&M", "m and m": "M&M"}
SEPARATOR_RE = re.compile(r"[，,、；;。\n]+")
LOCATION_RE = re.compile(r"(?:我)?(?:在|喺)([^，,、。\s]+)")
FILLER_RE = re.compile(r"^(?:我想買|想買|幫我搵|幫我買|買|同|和|及|還有|仲有|我喺[^\s，,、。]+想買)")
TOKEN_RE = re.compile(rf"(?P<qty>[0-9]+|[一二兩三四五六七八九十])?\s*(?P<unit>{UNIT_RE})?\s*(?P<kw>[A-Za-z0-9]*[&'][A-Za-z0-9'&]+|[A-Za-z0-9]+(?:\s+(?:and|[A-Za-z0-9]+))*|[\u4e00-\u9fff]+)", re.IGNORECASE)


def canonical_keyword(keyword: str) -> str:
    text = str(keyword or "").strip()
    return KEYWORD_CANONICAL.get(text, KEYWORD_CANONICAL.get(text.casefold(), text))


def extract_location_text(text: str) -> str | None:
    match = LOCATION_RE.search(text or "")
    return match.group(1).strip() if match else None


def _parse_quantity(raw: str | None) -> int:
    if not raw:
        return 1
    return int(raw) if raw.isdigit() else CHINESE_NUMBERS.get(raw, 1)


def _clean_segment(segment: str) -> str:
    segment = FILLER_RE.sub("", segment.strip())
    segment = re.sub(r"^(?:同|和|及|,|，|、)+", "", segment).strip()
    return segment


def _split_text(text: str) -> list[str]:
    normalized = str(text or "").strip()
    if not normalized:
        return []
    normalized = re.sub(r"\s+同\s+", " ", normalized)
    normalized = re.sub(r"同(?=[0-9一二兩三四五六七八九十])", " ", normalized)
    normalized = normalized.replace("\u548c", " ")
    pieces: list[str] = []
    for chunk in SEPARATOR_RE.split(normalized):
        chunk = chunk.strip()
        if not chunk:
            continue
        # Space separated real shopping lists should become separate pieces, but keep English brands with spaces.
        parts = chunk.split()
        buffer: list[str] = []
        for part in parts:
            if part.casefold() == "and" or (buffer and re.fullmatch(r"[A-Za-z]+", buffer[-1]) and re.fullmatch(r"[A-Za-z]+", part)):
                buffer.append(part)
            else:
                if buffer:
                    pieces.append(" ".join(buffer))
                buffer = [part]
        if buffer:
            pieces.append(" ".join(buffer))
    return pieces


def _keyword_from_text(raw_kw: str) -> str:
    kw = _clean_segment(raw_kw)
    for known in sorted(KNOWN_KEYWORDS, key=len, reverse=True):
        if known.casefold() == kw.casefold():
            return canonical_keyword(known)
    for known in sorted(KNOWN_KEYWORDS, key=len, reverse=True):
        if known.casefold() in kw.casefold():
            return canonical_keyword(known)
    return canonical_keyword(kw.strip())


def parse_simple_basket_text(text: str) -> list[dict[str, Any]]:
    items_by_key: dict[str, dict[str, Any]] = {}
    pending_qty: int | None = None
    pending_unit: str | None = None
    for segment in _split_text(text):
        raw_segment = segment.strip()
        segment = _clean_segment(segment)
        if not segment or not re.search(r"[A-Za-z0-9\u4e00-\u9fff]", segment):
            continue
        if segment.startswith(("我在", "我喺")) and "想買" not in segment:
            continue
        qty_only = re.fullmatch(rf"([0-9]+|[???????????])\s*({UNIT_RE})?", segment)
        if qty_only:
            pending_qty = _parse_quantity(qty_only.group(1))
            pending_unit = qty_only.group(2) or None
            continue
        match = TOKEN_RE.match(segment)
        if not match:
            continue
        qty = _parse_quantity(match.group("qty")) if match.group("qty") else (pending_qty or 1)
        unit = match.group("unit") or pending_unit
        pending_qty = None
        pending_unit = None
        keyword = _keyword_from_text(match.group("kw") or segment)
        if not keyword or keyword in {"\u6771\u897f", "\u5622", "\u5546\u54c1"} or keyword.startswith(("\u6211\u5728", "\u6211\u55ba")):
            continue
        existing = items_by_key.get(keyword)
        if existing:
            existing["quantity"] += qty
            if not existing.get("unit") and unit:
                existing["unit"] = unit
            existing["raw_text"] = f"{existing.get('raw_text', '')} {raw_segment}".strip()
        else:
            item: dict[str, Any] = {"keyword": keyword, "quantity": qty, "raw_text": raw_segment}
            if unit:
                item["unit"] = unit
            items_by_key[keyword] = item
    return list(items_by_key.values())

