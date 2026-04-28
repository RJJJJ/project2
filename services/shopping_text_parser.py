from __future__ import annotations

from typing import Any

from services.simple_basket_parser import parse_simple_basket_text


def parse_shopping_text(text: str) -> list[dict[str, Any]]:
    return [{"keyword": item["keyword"], "quantity": item.get("quantity", 1)} for item in parse_simple_basket_text(text)]
