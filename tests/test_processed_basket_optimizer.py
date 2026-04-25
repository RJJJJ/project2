from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.processed_basket_optimizer import (
    optimize_basket_cheapest_by_item,
    parse_items_arg,
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
                "product_name": "潘婷 去屑洗髮乳",
                "quantity": "750毫升",
                "category_id": 10,
                "category_name": "個人護理",
                "supermarket_oid": 52,
                "price_mop": 30.0,
                "discount": "",
                "distance_m": 500,
            },
        ],
    )
    return tmp_path


def test_parse_items_arg() -> None:
    assert parse_items_arg("米:1,洗頭水:2") == [
        {"keyword": "米", "quantity": 1},
        {"keyword": "洗頭水", "quantity": 2},
    ]


def test_single_item_selects_lowest_price(tmp_path: Path) -> None:
    processed_root = make_fixture(tmp_path)

    result = optimize_basket_cheapest_by_item(
        "2026-04-25",
        "p001",
        [{"keyword": "米", "quantity": 1}],
        processed_root,
    )

    assert result["items"][0]["supermarket_oid"] == 175
    assert result["items"][0]["unit_price_mop"] == 128.0
    assert result["items"][0]["matched_alias"] == "米"
    assert result["estimated_total_mop"] == 128.0


def test_multiple_items_total_calculation(tmp_path: Path) -> None:
    processed_root = make_fixture(tmp_path)

    result = optimize_basket_cheapest_by_item(
        "2026-04-25",
        "p001",
        [{"keyword": "米", "quantity": 1}, {"keyword": "洗頭水", "quantity": 2}],
        processed_root,
    )

    assert [item["subtotal_mop"] for item in result["items"]] == [128.0, 60.0]
    assert [item["matched_alias"] for item in result["items"]] == ["米", "洗髮乳"]
    assert result["estimated_total_mop"] == 188.0


def test_missing_item_adds_warning(tmp_path: Path) -> None:
    processed_root = make_fixture(tmp_path)

    result = optimize_basket_cheapest_by_item(
        "2026-04-25",
        "p001",
        [{"keyword": "不存在", "quantity": 1}],
        processed_root,
    )

    assert result["items"] == []
    assert result["warnings"] == ["No price records found for keyword: 不存在. Tried aliases: 不存在"]
