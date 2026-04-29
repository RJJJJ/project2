from __future__ import annotations

import json
import os
import re
from typing import Any
from urllib import error, request

from services.simple_basket_parser import parse_simple_basket_text

DEFAULT_LOCAL_LLM_ENDPOINT = "http://localhost:11434/api/generate"
DEFAULT_LOCAL_LLM_MODEL = "qwen3:4b"
_ALLOWED_GOALS = {"cheapest", "single_store", "nearby", "unknown"}
_ALLOWED_LANGUAGES = {"zh-HK", "zh-TW", "zh-CN", "en", "mixed"}
_ALLOWED_CONFIDENCE = {"high", "medium", "low"}
_CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")
_SEGMENT_SPLIT_RE = re.compile(
    r"[\uFF0C,\u3001\uFF1B;\u3002\n]+|\s+(?:\u540c|\u548c|\u53ca|\u4ef2\u6709|\u9084\u6709)\s+|"
    r"(?<=[A-Za-z0-9\u4e00-\u9fff])\u540c(?=[A-Za-z0-9\u4e00-\u9fff])"
)
_HEURISTIC_ITEM_RE = re.compile(
    r"(?P<qty>[0-9]+|[\u4e00\u4e8c\u5169\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341]|\u5e7e)?\s*"
    r"(?P<unit>\u5305|\u652f|\u679d|\u76d2|\u500b|\u74f6|\u6a3d|\u888b|\u7f50|\u689d|\u5377|\u6392|\u6253)?\s*"
    r"(?P<raw>[A-Za-z0-9&'\-]+|[\u4e00-\u9fff]+)"
)
_FILLER_PATTERNS = [
    r"^\u6211\u60f3\u8cb7",
    r"^\u60f3\u8cb7",
    r"^\u9806\u4fbf\u8cb7",
    r"^\u5e6b\u6211\u640f",
    r"^\u5e6b\u6211\u8cb7",
    r"^\u4eca\u665a\u6253\u908a\u7210",
    r"^\u6253\u908a\u7210",
    r"^\u6700\u597d",
    r"^\u76e1\u91cf",
]
_HK_HINT_TOKENS = ("\u5605", "\u55ba", "\u5572", "\u6253\u908a\u7210", "\u5e73\u5572", "\u5e7e\u652f")
_SINGLE_STORE_TOKENS = ("\u4e00\u9593", "\u540c\u4e00\u9593", "\u55ae\u4e00\u8d85\u5e02", "single store")
_NEARBY_TOKENS = ("\u9644\u8fd1", "\u5c31\u8fd1", "nearby")
_CHEAPEST_TOKENS = ("\u5e73\u5572", "\u6700\u5e73", "\u4fbf\u5b9c", "cheapest", "\u62b5\u8cb7")
_LOCATION_RE = re.compile(r"(?:\u6211)?(?:\u5728|\u55ba)([^\uFF0C,\u3001\u3002\s]+)")
_WARNING_FEW_UNITS = "\u5e7e\u652f interpreted as 3"
_DROP_RAW_TOKENS = {
    "\u4eca\u665a\u6253\u908a\u7210",
    "\u6253\u908a\u7210",
    "\u6700\u597d\u5e73\u5572",
    "\u5e73\u5572",
    "\u6700\u597d",
}
_HIGH_RISK_SHORT_RAWS = {
    "\u6cb9",
    "\u7cd6",
    "\u9eb5",
    "\u7c73",
    "\u5976",
    "\u6731\u53e4\u529b",
    "\u7d19\u5dfe",
}


def _detect_language(text: str) -> str:
    value = str(text or "")
    has_cjk = bool(_CHINESE_RE.search(value))
    has_ascii = bool(re.search(r"[A-Za-z]", value))
    if has_cjk and has_ascii:
        return "mixed"
    if has_cjk:
        if any(token in value for token in _HK_HINT_TOKENS):
            return "zh-HK"
        return "zh-TW"
    if has_ascii:
        return "en"
    return "mixed"


def _goal_from_query(query: str) -> str:
    text = str(query or "")
    if any(token in text for token in _SINGLE_STORE_TOKENS):
        return "single_store"
    if any(token in text for token in _NEARBY_TOKENS):
        return "nearby"
    if any(token in text for token in _CHEAPEST_TOKENS):
        return "cheapest"
    return "cheapest"


def _location_hint(query: str) -> str | None:
    match = _LOCATION_RE.search(str(query or ""))
    return match.group(1).strip() if match else None


def _normalize_unit(unit: Any) -> str | None:
    value = str(unit or "").strip()
    return value or None


def _normalize_item(item: dict[str, Any]) -> dict[str, Any] | None:
    raw = str(item.get("raw") or "").strip()
    if not raw:
        return None
    quantity = item.get("quantity")
    try:
        quantity_value = int(quantity) if quantity is not None else 1
    except (TypeError, ValueError):
        quantity_value = 1
    if quantity_value <= 0:
        quantity_value = 1
    notes = item.get("notes")
    notes_value = str(notes).strip() if notes not in {None, ""} else None
    if not notes_value:
        notes_value = None
    return {
        "raw": raw,
        "quantity": quantity_value,
        "unit": _normalize_unit(item.get("unit")),
        "notes": notes_value,
    }


def _planner_prompt(query: str) -> str:
    return f"""
\u4f60\u662f Project2 \u7684 query planner\u3002
\u4efb\u52d9\u662f\u628a\u6fb3\u9580\u8d85\u5e02\u8cfc\u7269\u67e5\u50f9 query \u8f49\u6210 strict JSON\u3002
\u4f60\u4e0d\u80fd\u56de\u7b54\u50f9\u683c\u3002
\u4f60\u4e0d\u80fd\u63a8\u85a6\u8d85\u5e02\u3002
\u4f60\u4e0d\u80fd\u67e5\u5546\u54c1\u3002
\u4f60\u4e0d\u80fd\u628a\u672a\u6536\u9304\u5546\u54c1\u6539\u6210\u76f8\u4f3c\u5546\u54c1\u3002
\u4f60\u53ea\u80fd\u62bd\u53d6\u8cfc\u7269 item\u3001quantity\u3001unit\u3001optimization goal\u3001location hint\u3002
\u4fdd\u7559\u539f\u59cb\u5546\u54c1\u8a5e\u3002
\u5982\u679c\u4e0d\u78ba\u5b9a\uff0c\u4ecd\u4fdd\u7559 raw item\uff0cconfidence \u8a2d\u70ba low \u6216 medium\u3002
\u53ea\u8f38\u51fa JSON\uff0c\u4e0d\u8981 markdown\uff0c\u4e0d\u8981\u89e3\u91cb\u3002

JSON schema:
{{
  "task_type": "basket_price_optimization",
  "language": "zh-HK" | "zh-TW" | "zh-CN" | "en" | "mixed",
  "items": [
    {{"raw": "string", "quantity": number | null, "unit": "string" | null, "notes": "string" | null}}
  ],
  "optimization_goal": "cheapest" | "single_store" | "nearby" | "unknown",
  "location_hint": "string" | null,
  "confidence": "high" | "medium" | "low",
  "warnings": []
}}

Example 1:
Input:
\u5169\u5305\u9eb5 \u4e00\u5305\u85af\u689d \u56db\u5305\u85af\u7247 \u6cb9 \u7cd6 M&M
Output:
{{
  "task_type": "basket_price_optimization",
  "language": "mixed",
  "items": [
    {{"raw": "\u9eb5", "quantity": 2, "unit": "\u5305", "notes": null}},
    {{"raw": "\u85af\u689d", "quantity": 1, "unit": "\u5305", "notes": null}},
    {{"raw": "\u85af\u7247", "quantity": 4, "unit": "\u5305", "notes": null}},
    {{"raw": "\u6cb9", "quantity": 1, "unit": null, "notes": null}},
    {{"raw": "\u7cd6", "quantity": 1, "unit": null, "notes": null}},
    {{"raw": "M&M", "quantity": 1, "unit": null, "notes": null}}
  ],
  "optimization_goal": "cheapest",
  "location_hint": null,
  "confidence": "high",
  "warnings": []
}}

Example 2:
Input:
\u6211\u60f3\u8cb7\u7802\u7cd6\u540c\u6d17\u982d\u6c34
Output:
{{
  "task_type": "basket_price_optimization",
  "language": "zh-HK",
  "items": [
    {{"raw": "\u7802\u7cd6", "quantity": 1, "unit": null, "notes": null}},
    {{"raw": "\u6d17\u982d\u6c34", "quantity": 1, "unit": null, "notes": null}}
  ],
  "optimization_goal": "cheapest",
  "location_hint": null,
  "confidence": "high",
  "warnings": []
}}

Example 3:
Input:
\u4eca\u665a\u6253\u908a\u7210\uff0c\u60f3\u8cb7\u5e7e\u652f\u98f2\u54c1\u3001\u7d19\u5dfe\u540c\u4e00\u5305\u7c73\uff0c\u6700\u597d\u5e73\u5572
Output:
{{
  "task_type": "basket_price_optimization",
  "language": "zh-HK",
  "items": [
    {{"raw": "\u98f2\u54c1", "quantity": 3, "unit": "\u652f", "notes": "\u5e7e\u652f interpreted as 3"}},
    {{"raw": "\u7d19\u5dfe", "quantity": 1, "unit": null, "notes": null}},
    {{"raw": "\u7c73", "quantity": 1, "unit": "\u5305", "notes": null}}
  ],
  "optimization_goal": "cheapest",
  "location_hint": null,
  "confidence": "medium",
  "warnings": ["\u5e7e\u652f interpreted as 3"]
}}

Input:
{query}
Output:
""".strip()


def _extract_json_object(text: str) -> dict[str, Any]:
    raw = str(text or "").strip()
    if not raw:
        raise ValueError("Local LLM returned empty output")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            return json.loads(raw[start : end + 1])
        raise ValueError("Local LLM did not return valid JSON") from None


def _heuristic_segments(query: str) -> list[str]:
    text = str(query or "").strip()
    if not text:
        return []
    segments = []
    for segment in _SEGMENT_SPLIT_RE.split(text):
        value = str(segment or "").strip()
        for pattern in _FILLER_PATTERNS:
            value = re.sub(pattern, "", value)
        value = value.strip(" \uFF0C,\u3001\uFF1B;\u3002")
        if value:
            segments.append(value)
    return segments


def _heuristic_items(query: str) -> tuple[list[dict[str, Any]], list[str]]:
    items: list[dict[str, Any]] = []
    warnings: list[str] = []
    for segment in _heuristic_segments(query):
        match = _HEURISTIC_ITEM_RE.search(segment)
        if not match:
            continue
        raw = str(match.group("raw") or "").strip()
        if not raw or raw in _DROP_RAW_TOKENS:
            continue
        qty_token = match.group("qty")
        unit_token = match.group("unit")
        quantity = 1
        notes = None
        if qty_token == "\u5e7e":
            quantity = 3
            notes = _WARNING_FEW_UNITS
            warnings.append(notes)
        elif qty_token and qty_token.isdigit():
            quantity = max(1, int(qty_token))
        elif qty_token:
            quantity = {
                "\u4e00": 1,
                "\u4e8c": 2,
                "\u5169": 2,
                "\u4e09": 3,
                "\u56db": 4,
                "\u4e94": 5,
                "\u516d": 6,
                "\u4e03": 7,
                "\u516b": 8,
                "\u4e5d": 9,
                "\u5341": 10,
            }.get(qty_token, 1)
        items.append({"raw": raw, "quantity": quantity, "unit": unit_token or None, "notes": notes})
    deduped: dict[str, dict[str, Any]] = {}
    for item in items:
        raw = item["raw"]
        if raw not in deduped:
            deduped[raw] = item
        else:
            deduped[raw]["quantity"] = int(deduped[raw].get("quantity") or 1) + int(item.get("quantity") or 1)
            if not deduped[raw].get("unit") and item.get("unit"):
                deduped[raw]["unit"] = item.get("unit")
    return list(deduped.values()), list(dict.fromkeys(warnings))


def _looks_like_parser_noise(items: list[dict[str, Any]]) -> bool:
    noisy_terms = _DROP_RAW_TOKENS | {
        "\u5e7e\u652f\u98f2\u54c1",
        "\u6211\u60f3\u8cb7",
        "\u60f3\u8cb7",
    }
    raws = [str(item.get("raw") or "").strip() for item in items]
    return any(raw in noisy_terms for raw in raws)


def _prefer_heuristic_items(parser_items: list[dict[str, Any]], heuristic_items: list[dict[str, Any]]) -> bool:
    if not heuristic_items:
        return False
    if _looks_like_parser_noise(parser_items):
        return True
    if len(parser_items) != len(heuristic_items):
        return len(heuristic_items) > len(parser_items)
    for parser_item, heuristic_item in zip(parser_items, heuristic_items):
        parser_raw = str(parser_item.get("raw") or "").strip()
        heuristic_raw = str(heuristic_item.get("raw") or "").strip()
        if parser_raw in _HIGH_RISK_SHORT_RAWS and heuristic_raw and heuristic_raw != parser_raw and parser_raw in heuristic_raw:
            return True
    return False


def plan_query_with_local_llm(
    query: str,
    model: str | None = None,
    endpoint: str | None = None,
    timeout_seconds: int = 20,
) -> dict[str, Any]:
    selected_model = model or os.getenv("PROJECT2_LOCAL_LLM_MODEL") or DEFAULT_LOCAL_LLM_MODEL
    selected_endpoint = endpoint or os.getenv("PROJECT2_LOCAL_LLM_ENDPOINT") or DEFAULT_LOCAL_LLM_ENDPOINT
    payload = {
        "model": selected_model,
        "prompt": _planner_prompt(query),
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
    }
    req = request.Request(
        selected_endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=max(1, int(timeout_seconds))) as response:
            body = response.read().decode("utf-8")
    except error.URLError as exc:
        raise RuntimeError(f"Local LLM endpoint unavailable: {exc}") from exc
    except TimeoutError as exc:
        raise RuntimeError("Local LLM request timed out") from exc
    data = _extract_json_object(body)
    if isinstance(data, dict) and "response" in data:
        return _extract_json_object(str(data.get("response") or ""))
    return data


def plan_query_with_rule_fallback(query: str) -> dict[str, Any]:
    warnings: list[str] = []
    parsed_items = parse_simple_basket_text(query)
    parser_items = [
            {
                "raw": str(parsed.get("keyword") or parsed.get("raw_text") or "").strip(),
                "quantity": parsed.get("quantity", 1),
                "unit": _normalize_unit(parsed.get("unit")),
                "notes": None,
            }
            for parsed in parsed_items
            if str(parsed.get("keyword") or parsed.get("raw_text") or "").strip()
        ]
    heuristic_items, warnings = _heuristic_items(query)
    if parser_items and not _prefer_heuristic_items(parser_items, heuristic_items):
        items = parser_items
        confidence = "high"
    else:
        items = heuristic_items
        confidence = "medium" if items else "low"
    return normalize_planner_items(
        {
            "task_type": "basket_price_optimization",
            "language": _detect_language(query),
            "items": items,
            "optimization_goal": _goal_from_query(query),
            "location_hint": _location_hint(query),
            "confidence": confidence,
            "warnings": warnings,
        }
    )


def validate_planner_output(payload: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return False, ["Planner output must be an object"]
    if payload.get("task_type") != "basket_price_optimization":
        errors.append("task_type must be basket_price_optimization")
    if payload.get("language") not in _ALLOWED_LANGUAGES:
        errors.append("language is invalid or missing")
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        errors.append("items must be a non-empty list")
    else:
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"items[{index}] must be an object")
                continue
            raw = str(item.get("raw") or "").strip()
            if not raw:
                errors.append(f"items[{index}].raw is required")
            quantity = item.get("quantity")
            if quantity is not None and not isinstance(quantity, (int, float)):
                errors.append(f"items[{index}].quantity must be numeric or null")
    if payload.get("optimization_goal") not in _ALLOWED_GOALS:
        errors.append("optimization_goal is invalid or missing")
    if payload.get("confidence") not in _ALLOWED_CONFIDENCE:
        errors.append("confidence is invalid or missing")
    warnings = payload.get("warnings")
    if warnings is not None and not isinstance(warnings, list):
        errors.append("warnings must be a list")
    return not errors, errors


def normalize_planner_items(payload: dict[str, Any]) -> dict[str, Any]:
    normalized_items: list[dict[str, Any]] = []
    for item in payload.get("items") or []:
        if isinstance(item, dict):
            normalized = _normalize_item(item)
            if normalized:
                normalized_items.append(normalized)
    return {
        "task_type": "basket_price_optimization",
        "language": payload.get("language") if payload.get("language") in _ALLOWED_LANGUAGES else "mixed",
        "items": normalized_items,
        "optimization_goal": payload.get("optimization_goal") if payload.get("optimization_goal") in _ALLOWED_GOALS else "unknown",
        "location_hint": str(payload.get("location_hint") or "").strip() or None,
        "confidence": payload.get("confidence") if payload.get("confidence") in _ALLOWED_CONFIDENCE else "low",
        "warnings": [str(item) for item in (payload.get("warnings") or []) if str(item).strip()],
    }
