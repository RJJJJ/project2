from __future__ import annotations

from collections.abc import Iterable
from typing import Any


EMPTY_PRICE_VALUES = {"", "--", "-", "null", "NULL", "None", "none"}


def normalize_price(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "")
        if cleaned in EMPTY_PRICE_VALUES:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _first_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if not isinstance(value, dict):
        return []

    for key in ("data", "items", "list", "rows", "result", "results"):
        nested = value.get(key)
        if isinstance(nested, list):
            return [item for item in nested if isinstance(item, dict)]
        if isinstance(nested, dict):
            nested_list = _first_list(nested)
            if nested_list:
                return nested_list
    return []


def _name_from_multilang(value: Any, preferred: str = "cn") -> str | None:
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return None
    for key in (preferred, "zh", "zh_hant", "name_cn", "cn_name", "name", "en"):
        candidate = value.get(key)
        if candidate:
            return str(candidate)
    return None


def _category_fields(item: dict[str, Any]) -> dict[str, Any]:
    category = item.get("category") if isinstance(item.get("category"), dict) else {}
    category_name_value = item.get("category_name") or category.get("name")

    return {
        "category_oid": category.get("oid") or category.get("id") or item.get("category_oid"),
        "category_name_cn": (
            category.get("name_cn")
            or category.get("cn")
            or category.get("zh")
            or _name_from_multilang(category_name_value, preferred="cn")
        ),
        "category_name_en": (
            category.get("name_en")
            or category.get("en")
            or _name_from_multilang(category.get("name_en"), preferred="en")
        ),
    }


def _iter_supermarkets(item: dict[str, Any]) -> Iterable[dict[str, Any]]:
    supermarkets = item.get("supermarkets") or []
    if not isinstance(supermarkets, list):
        return []
    return [supermarket for supermarket in supermarkets if isinstance(supermarket, dict)]


def flatten_items_price_response(
    data: dict[str, Any] | list[Any],
    source_url: str,
    lat: float,
    lng: float,
    dst: int,
) -> list[dict[str, Any]]:
    items = _first_list(data)
    rows: list[dict[str, Any]] = []

    for item in items:
        category_fields = _category_fields(item)
        category_name = _name_from_multilang(item.get("category_name")) or category_fields["category_name_cn"]
        product_name = _name_from_multilang(item.get("name"))

        for supermarket in _iter_supermarkets(item):
            rows.append(
                {
                    "product_oid": item.get("oid"),
                    "product_name": product_name,
                    "quantity": item.get("quantity"),
                    "category_id": item.get("category_id"),
                    "category_name": category_name,
                    "category_oid": category_fields["category_oid"],
                    "category_name_cn": category_fields["category_name_cn"],
                    "category_name_en": category_fields["category_name_en"],
                    "supermarket_code": supermarket.get("supermarket_code"),
                    "price_mop": normalize_price(supermarket.get("price")),
                    "discount": supermarket.get("discount"),
                    "flag": supermarket.get("flag"),
                    "source_url": source_url,
                    "center_lat": lat,
                    "center_lng": lng,
                    "distance_m": dst,
                }
            )

    return rows
