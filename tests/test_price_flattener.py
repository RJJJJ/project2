from __future__ import annotations

from services.price_flattener import (
    clean_price,
    flatten_items_price_response,
    flatten_supermarkets_response,
)


def test_clean_price() -> None:
    assert clean_price("12.3") == 12.3
    assert clean_price("--") is None
    assert clean_price("") is None
    assert clean_price(None) is None


def test_flatten_supermarkets_response() -> None:
    data = {
        "success": 1,
        "data": {
            "itemsPrice": [],
            "supermarkets": [
                {"_id": "abc", "oid": 175, "name": "高士德 新花城超市"},
                {"_id": "def", "oid": 52, "name": "世紀豪庭 新苗超市"},
            ],
        },
        "error": -1,
    }

    rows = flatten_supermarkets_response(data, "p001", "https://example.test/source", 500)

    assert rows == [
        {
            "point_code": "p001",
            "supermarket_oid": 175,
            "supermarket_id": "abc",
            "supermarket_name": "高士德 新花城超市",
            "distance_m": 500,
            "source_url": "https://example.test/source",
            "raw_payload": {"_id": "abc", "oid": 175, "name": "高士德 新花城超市"},
        },
        {
            "point_code": "p001",
            "supermarket_oid": 52,
            "supermarket_id": "def",
            "supermarket_name": "世紀豪庭 新苗超市",
            "distance_m": 500,
            "source_url": "https://example.test/source",
            "raw_payload": {"_id": "def", "oid": 52, "name": "世紀豪庭 新苗超市"},
        },
    ]


def test_flatten_items_price_response() -> None:
    data = {
        "success": 1,
        "data": {
            "itemsPrice": [
                {
                    "oid": 18,
                    "name": "青靈芝香米（新花）",
                    "quantity": "10公斤",
                    "category_id": 1,
                    "category_name": "米類",
                    "supermarkets": [
                        {"supermarket_code": 52, "price": "130.0", "discount": "", "flag": ""},
                        {"supermarket_code": 175, "price": "--", "discount": "yes", "flag": "new"},
                    ],
                }
            ],
            "supermarkets": [],
        },
    }

    rows = flatten_items_price_response(data, "p001", 1, "https://example.test/source", 500)

    assert len(rows) == 2
    assert rows[0]["point_code"] == "p001"
    assert rows[0]["product_oid"] == 18
    assert rows[0]["product_name"] == "青靈芝香米（新花）"
    assert rows[0]["quantity"] == "10公斤"
    assert rows[0]["category_id"] == 1
    assert rows[0]["category_name"] == "米類"
    assert rows[0]["supermarket_oid"] == 52
    assert rows[0]["price_mop"] == 130.0
    assert rows[0]["discount"] == ""
    assert rows[0]["flag"] == ""
    assert rows[0]["distance_m"] == 500
    assert rows[0]["source_url"] == "https://example.test/source"
    assert rows[0]["raw_payload"]["item"]["oid"] == 18
    assert rows[0]["raw_payload"]["supermarket"]["supermarket_code"] == 52

    assert rows[1]["supermarket_oid"] == 175
    assert rows[1]["price_mop"] is None
