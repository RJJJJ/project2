from __future__ import annotations

from typing import Any


EMPTY_PRICE_VALUES = {"", "--", "-", "null", "NULL", "None", "none"}


def clean_price(value: Any) -> float | None:
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


def _data_node(data: dict[str, Any] | list[Any]) -> dict[str, Any]:
    if isinstance(data, dict) and isinstance(data.get("data"), dict):
        return data["data"]
    if isinstance(data, dict):
        return data
    return {}


def _list_from_data(data: dict[str, Any] | list[Any], key: str) -> list[dict[str, Any]]:
    node = _data_node(data)
    value = node.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def flatten_supermarkets_response(
    data: dict[str, Any] | list[Any],
    point_code: str,
    source_url: str,
    distance_m: int | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for supermarket in _list_from_data(data, "supermarkets"):
        rows.append(
            {
                "point_code": point_code,
                "supermarket_oid": supermarket.get("oid"),
                "supermarket_id": supermarket.get("_id"),
                "supermarket_name": supermarket.get("name"),
                "distance_m": distance_m,
                "source_url": source_url,
                "raw_payload": supermarket,
            }
        )
    return rows


def flatten_items_price_response(
    data: dict[str, Any] | list[Any],
    point_code: str,
    category_id: int,
    source_url: str,
    distance_m: int | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in _list_from_data(data, "itemsPrice"):
        supermarkets = item.get("supermarkets")
        if not isinstance(supermarkets, list):
            supermarkets = []

        for supermarket in supermarkets:
            if not isinstance(supermarket, dict):
                continue
            rows.append(
                {
                    "point_code": point_code,
                    "product_oid": item.get("oid"),
                    "product_name": item.get("name"),
                    "quantity": item.get("quantity"),
                    "category_id": item.get("category_id", category_id),
                    "category_name": item.get("category_name"),
                    "supermarket_oid": supermarket.get("supermarket_code"),
                    "price_mop": clean_price(supermarket.get("price")),
                    "discount": supermarket.get("discount"),
                    "flag": supermarket.get("flag"),
                    "distance_m": distance_m,
                    "source_url": source_url,
                    "raw_payload": {
                        "item": item,
                        "supermarket": supermarket,
                    },
                }
            )
    return rows
