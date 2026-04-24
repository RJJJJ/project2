from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.processed_price_query import (
    get_cheapest_prices_for_keyword,
    get_prices_for_keyword,
    search_products,
)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def make_fixture(tmp_path: Path) -> Path:
    point_dir = tmp_path / "2026-04-25" / "p001"
    write_jsonl(
        point_dir / "supermarkets.jsonl",
        [
            {"point_code": "p001", "supermarket_oid": 52, "supermarket_name": "世紀豪庭 新苗超市"},
            {"point_code": "p001", "supermarket_oid": 175, "supermarket_name": "高士德 新花城超市"},
        ],
    )
    write_jsonl(
        point_dir / "category_1_prices.jsonl",
        [
            {
                "point_code": "p001",
                "product_oid": 18,
                "product_name": "青靈芝香米（新花）",
                "quantity": "10公斤",
                "category_id": 1,
                "category_name": "米類",
                "supermarket_oid": 52,
                "price_mop": 130.0,
                "discount": "",
                "distance_m": 500,
            },
            {
                "point_code": "p001",
                "product_oid": 18,
                "product_name": "青靈芝香米（新花）",
                "quantity": "10公斤",
                "category_id": 1,
                "category_name": "米類",
                "supermarket_oid": 175,
                "price_mop": 128.0,
                "discount": "",
                "distance_m": 500,
            },
            {
                "point_code": "p001",
                "product_oid": 99,
                "product_name": "花生油",
                "quantity": "900毫升",
                "category_id": 10,
                "category_name": "食油",
                "supermarket_oid": 52,
                "price_mop": 30.0,
                "discount": "",
                "distance_m": 500,
            },
        ],
    )
    return tmp_path


def test_supermarket_join_is_correct(tmp_path: Path) -> None:
    processed_root = make_fixture(tmp_path)

    rows = get_prices_for_keyword("2026-04-25", "p001", "米", processed_root)

    assert len(rows) == 2
    assert rows[0]["supermarket_name"] == "世紀豪庭 新苗超市"
    assert rows[1]["supermarket_name"] == "高士德 新花城超市"


def test_keyword_search_is_correct(tmp_path: Path) -> None:
    processed_root = make_fixture(tmp_path)

    products = search_products("2026-04-25", "p001", "米", processed_root)

    assert products == [
        {
            "product_oid": 18,
            "product_name": "青靈芝香米（新花）",
            "quantity": "10公斤",
            "category_id": 1,
            "category_name": "米類",
        }
    ]


def test_cheapest_sort_is_correct(tmp_path: Path) -> None:
    processed_root = make_fixture(tmp_path)

    rows = get_cheapest_prices_for_keyword("2026-04-25", "p001", "米", limit=10, processed_root=processed_root)

    assert [row["supermarket_oid"] for row in rows] == [175, 52]
    assert [row["price_mop"] for row in rows] == [128.0, 130.0]
