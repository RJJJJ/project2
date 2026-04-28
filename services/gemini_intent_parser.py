from __future__ import annotations

import json
import os
import re
from typing import Any

from services.simple_basket_parser import extract_location_text, parse_simple_basket_text

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")


def _fallback_intent(text: str, confidence: float = 0.55) -> dict[str, Any]:
    items = parse_simple_basket_text(text)
    return {
        "location_text": extract_location_text(text),
        "point_code": None,
        "items": [
            {
                "keyword": item["keyword"],
                "quantity": item.get("quantity", 1),
                "unit": item.get("unit"),
                "raw_text": item.get("raw_text", item["keyword"]),
            }
            for item in items
        ],
        "preference": None,
        "needs_clarification": not bool(items),
        "clarification_question": None if items else "\u8acb\u8f38\u5165\u60f3\u8cb7\u7684\u5546\u54c1\u3002",
        "confidence": confidence,
    }


def _extract_text(response: Any) -> str:
    if isinstance(response, str):
        return response
    text = getattr(response, "text", None)
    if isinstance(text, str):
        return text
    if isinstance(response, dict):
        return str(response.get("text") or response.get("content") or "")
    return str(response or "")


def _parse_json_text(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL | re.IGNORECASE)
    if fenced:
        cleaned = fenced.group(1).strip()
    return json.loads(cleaned)


def _validate_intent(data: dict[str, Any], original_text: str) -> dict[str, Any]:
    fallback = _fallback_intent(original_text)
    items = data.get("items") if isinstance(data.get("items"), list) else fallback["items"]
    normalized_items = []
    for item in items:
        if not isinstance(item, dict) or not str(item.get("keyword") or "").strip():
            continue
        normalized_items.append(
            {
                "keyword": str(item.get("keyword") or "").strip(),
                "quantity": float(item.get("quantity") or 1),
                "unit": item.get("unit"),
                "raw_text": str(item.get("raw_text") or item.get("keyword") or ""),
            }
        )
    return {
        "location_text": data.get("location_text") or fallback["location_text"],
        "point_code": data.get("point_code"),
        "items": normalized_items,
        "preference": data.get("preference"),
        "needs_clarification": bool(data.get("needs_clarification", not bool(normalized_items))),
        "clarification_question": data.get("clarification_question"),
        "confidence": float(data.get("confidence", 0.75)),
    }


def _prompt(text: str) -> str:
    return (
        "You extract shopping intent only. Return strict JSON only. "
        "Never invent prices, stores, totals, discounts, or product availability. "
        "Schema: location_text string|null, point_code string|null, items array of "
        "{keyword, quantity, unit, raw_text}, preference cheapest|single_store|two_stores|balanced|null, "
        "needs_clarification boolean, clarification_question string|null, confidence number.\n"
        f"User text: {text}"
    )


def _call_client(client: Any, model_name: str, prompt: str) -> Any:
    if hasattr(client, "models") and hasattr(client.models, "generate_content"):
        return client.models.generate_content(model=model_name, contents=prompt)
    if hasattr(client, "generate_content"):
        try:
            return client.generate_content(model=model_name, contents=prompt)
        except TypeError:
            return client.generate_content(prompt)
    raise TypeError("Unsupported Gemini client interface")


def parse_intent(text: str, *, use_gemini: bool = True, model_name: str | None = None, client: Any | None = None) -> dict[str, Any]:
    if not use_gemini:
        return _fallback_intent(text)
    model = model_name or DEFAULT_MODEL
    if client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return _fallback_intent(text)
        try:
            from google import genai  # type: ignore

            client = genai.Client(api_key=api_key)
        except Exception:
            return _fallback_intent(text)
    try:
        response = _call_client(client, model, _prompt(text))
        data = _parse_json_text(_extract_text(response))
        if not isinstance(data, dict):
            return _fallback_intent(text)
        return _validate_intent(data, text)
    except Exception:
        return _fallback_intent(text)
