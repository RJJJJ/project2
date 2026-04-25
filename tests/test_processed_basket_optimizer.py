from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.processed_basket_optimizer import (
    optimize_basket,
    optimize_basket_cheapest_by_item,
    optimize_basket_cheapest_single_store,
    optimize_basket_cheapest_two_stores,
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
    assert result["store_count"] == 1
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


def make_multi_store_fixture(tmp_path: Path) -> Path:
    point_dir = tmp_path / "2026-04-25" / "p001"
    write_jsonl(
        point_dir / "supermarkets.jsonl",
        [
            {"point_code": "p001", "supermarket_oid": 1, "supermarket_name": "Store A"},
            {"point_code": "p001", "supermarket_oid": 2, "supermarket_name": "Store B"},
            {"point_code": "p001", "supermarket_oid": 3, "supermarket_name": "Store C"},
        ],
    )
    write_jsonl(
        point_dir / "category_1_prices.jsonl",
        [
            {
                "point_code": "p001",
                "product_oid": 101,
                "product_name": "香米",
                "quantity": "5公斤",
                "category_id": 1,
                "category_name": "米類",
                "supermarket_oid": 1,
                "price_mop": 60.0,
            },
            {
                "point_code": "p001",
                "product_oid": 101,
                "product_name": "香米",
                "quantity": "5公斤",
                "category_id": 1,
                "category_name": "米類",
                "supermarket_oid": 2,
                "price_mop": 65.0,
            },
            {
                "point_code": "p001",
                "product_oid": 102,
                "product_name": "潘婷 洗髮乳",
                "quantity": "750毫升",
                "category_id": 10,
                "category_name": "個人護理",
                "supermarket_oid": 2,
                "price_mop": 40.0,
            },
            {
                "point_code": "p001",
                "product_oid": 102,
                "product_name": "潘婷 洗髮乳",
                "quantity": "750毫升",
                "category_id": 10,
                "category_name": "個人護理",
                "supermarket_oid": 3,
                "price_mop": 30.0,
            },
            {
                "point_code": "p001",
                "product_oid": 103,
                "product_name": "Tempo 紙巾",
                "quantity": "6包",
                "category_id": 11,
                "category_name": "紙巾",
                "supermarket_oid": 1,
                "price_mop": 25.0,
            },
            {
                "point_code": "p001",
                "product_oid": 103,
                "product_name": "Tempo 紙巾",
                "quantity": "6包",
                "category_id": 11,
                "category_name": "紙巾",
                "supermarket_oid": 3,
                "price_mop": 20.0,
            },
        ],
    )
    return tmp_path


def test_single_store_can_cover_all_items(tmp_path: Path) -> None:
    processed_root = make_multi_store_fixture(tmp_path)
    items = parse_items_arg("米:1,洗頭水:1")

    result = optimize_basket_cheapest_single_store("2026-04-25", "p001", items, processed_root)

    assert result["store_count"] == 1
    assert result["stores"] == [{"supermarket_oid": 2, "supermarket_name": "Store B"}]
    assert result["estimated_total_mop"] == 105.0
    assert [item["supermarket_oid"] for item in result["items"]] == [2, 2]


def test_single_store_warning_when_no_store_covers_all_items(tmp_path: Path) -> None:
    processed_root = make_multi_store_fixture(tmp_path)
    items = parse_items_arg("米:1,洗頭水:1,紙巾:1")

    result = optimize_basket_cheapest_single_store("2026-04-25", "p001", items, processed_root)

    assert result["store_count"] == 0
    assert "No single store can cover all requested keywords." in result["warnings"]


def test_two_store_combination_covers_all_items(tmp_path: Path) -> None:
    processed_root = make_multi_store_fixture(tmp_path)
    items = parse_items_arg("米:1,洗頭水:1,紙巾:1")

    result = optimize_basket_cheapest_two_stores("2026-04-25", "p001", items, processed_root)

    assert result["store_count"] == 2
    assert result["items"] != []
    assert {store["supermarket_oid"] for store in result["stores"]} == {1, 3}
    assert result["estimated_total_mop"] == 110.0
    assert [item["supermarket_oid"] for item in result["items"]] == [1, 3, 3]


def test_cheapest_by_item_can_use_more_than_two_stores(tmp_path: Path) -> None:
    point_dir = tmp_path / "2026-04-25" / "p001"
    write_jsonl(
        point_dir / "supermarkets.jsonl",
        [
            {"point_code": "p001", "supermarket_oid": 1, "supermarket_name": "Store A"},
            {"point_code": "p001", "supermarket_oid": 2, "supermarket_name": "Store B"},
            {"point_code": "p001", "supermarket_oid": 3, "supermarket_name": "Store C"},
        ],
    )
    write_jsonl(
        point_dir / "category_1_prices.jsonl",
        [
            {
                "point_code": "p001",
                "product_oid": 101,
                "product_name": "香米",
                "quantity": "5公斤",
                "category_id": 1,
                "category_name": "米類",
                "supermarket_oid": 1,
                "price_mop": 60.0,
            },
            {
                "point_code": "p001",
                "product_oid": 102,
                "product_name": "潘婷 洗髮乳",
                "quantity": "750毫升",
                "category_id": 10,
                "category_name": "個人護理",
                "supermarket_oid": 2,
                "price_mop": 30.0,
            },
            {
                "point_code": "p001",
                "product_oid": 103,
                "product_name": "Tempo 紙巾",
                "quantity": "6包",
                "category_id": 11,
                "category_name": "紙巾",
                "supermarket_oid": 3,
                "price_mop": 20.0,
            },
        ],
    )
    items = parse_items_arg("米:1,洗頭水:1,紙巾:1")

    result = optimize_basket_cheapest_by_item("2026-04-25", "p001", items, tmp_path)

    assert result["store_count"] == 3
    assert [item["supermarket_oid"] for item in result["items"]] == [1, 2, 3]
    assert result["estimated_total_mop"] == 110.0


def test_optimize_basket_outputs_all_plans_and_totals(tmp_path: Path) -> None:
    processed_root = make_multi_store_fixture(tmp_path)
    items = parse_items_arg("米:2,洗頭水:1")

    result = optimize_basket("2026-04-25", "p001", items, processed_root)

    assert [plan["plan_type"] for plan in result["plans"]] == [
        "cheapest_by_item",
        "cheapest_single_store",
        "cheapest_two_stores",
    ]
    assert result["plans"][0]["estimated_total_mop"] == 150.0
    assert result["plans"][1]["estimated_total_mop"] == 170.0
    assert result["plans"][2]["estimated_total_mop"] == 150.0


def test_two_store_returns_non_empty_when_by_item_proves_two_stores_cover(tmp_path: Path) -> None:
    point_dir = tmp_path / "2026-04-25" / "p001"
    write_jsonl(
        point_dir / "supermarkets.jsonl",
        [
            {"point_code": "p001", "supermarket_oid": 10, "supermarket_name": "Store X"},
            {"point_code": "p001", "supermarket_oid": 20, "supermarket_name": "Store Y"},
        ],
    )
    write_jsonl(
        point_dir / "category_1_prices.jsonl",
        [
            {
                "point_code": "p001",
                "product_oid": 1,
                "product_name": "香米",
                "quantity": "5公斤",
                "category_id": 1,
                "category_name": "米類",
                "supermarket_oid": 10,
                "price_mop": 40.0,
            },
            {
                "point_code": "p001",
                "product_oid": 2,
                "product_name": "潘婷 洗髮乳",
                "quantity": "750毫升",
                "category_id": 10,
                "category_name": "個人護理",
                "supermarket_oid": 20,
                "price_mop": 20.0,
            },
            {
                "point_code": "p001",
                "product_oid": 3,
                "product_name": "Tempo 紙巾",
                "quantity": "6包",
                "category_id": 11,
                "category_name": "紙巾",
                "supermarket_oid": 20,
                "price_mop": 15.0,
            },
        ],
    )
    items = parse_items_arg("米:1,洗頭水:2,紙巾:1")

    by_item = optimize_basket_cheapest_by_item("2026-04-25", "p001", items, tmp_path)
    two_stores = optimize_basket_cheapest_two_stores("2026-04-25", "p001", items, tmp_path)
    single_store = optimize_basket_cheapest_single_store("2026-04-25", "p001", items, tmp_path)

    assert by_item["store_count"] == 2
    assert by_item["estimated_total_mop"] == 95.0
    assert single_store["store_count"] == 0
    assert single_store["items"] == []
    assert two_stores["store_count"] == 2
    assert two_stores["items"] != []
    assert two_stores["estimated_total_mop"] == 95.0
