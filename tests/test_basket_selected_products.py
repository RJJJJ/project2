
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.processed_basket_optimizer import optimize_basket


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
            {"point_code": "p001", "supermarket_oid": 1, "supermarket_name": "Store A"},
            {"point_code": "p001", "supermarket_oid": 2, "supermarket_name": "Store B"},
        ],
    )
    write_jsonl(
        point_dir / "category_1_prices.jsonl",
        [
            {"point_code": "p001", "product_oid": 101, "product_name": "\u5e73\u50f9\u9999\u7c73", "quantity": "1??", "category_id": 1, "category_name": "\u7c73\u985e", "supermarket_oid": 1, "price_mop": 12.0},
            {"point_code": "p001", "product_oid": 202, "product_name": "\u5bb6\u5ead\u88dd\u73cd\u73e0\u7c73", "quantity": "5??", "category_id": 1, "category_name": "\u7c73\u985e", "supermarket_oid": 2, "price_mop": 66.0},
        ],
    )
    return tmp_path


def test_selected_product_oid_limits_optimizer_to_selected_product(tmp_path: Path) -> None:
    processed_root = make_fixture(tmp_path)
    items = [{"keyword": "\u7c73", "quantity": 1, "selected_product_oid": 202}]

    result = optimize_basket("2026-04-25", "p001", items, processed_root)

    for plan in result["plans"]:
        assert plan["items"][0]["product_oid"] == 202
        assert plan["items"][0]["product_name"] == "\u5bb6\u5ead\u88dd\u73cd\u73e0\u7c73"
    assert result["warnings"] == []


def test_missing_selected_product_adds_warning(tmp_path: Path) -> None:
    processed_root = make_fixture(tmp_path)
    items = [{"keyword": "\u7c73", "quantity": 1, "selected_product_oid": 999}]

    result = optimize_basket("2026-04-25", "p001", items, processed_root)

    assert "Selected product not found for keyword: 米, product_oid: 999" in result["warnings"]
    assert result["plans"][0]["items"] == []


def test_without_selected_products_keeps_existing_cheapest_behavior(tmp_path: Path) -> None:
    processed_root = make_fixture(tmp_path)
    items = [{"keyword": "\u7c73", "quantity": 1}]

    result = optimize_basket("2026-04-25", "p001", items, processed_root)

    assert result["plans"][0]["items"][0]["product_oid"] == 101
    assert result["plans"][0]["items"][0]["unit_price_mop"] == 12.0
