from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.price_signal_analyzer import analyze_point_signals


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
            {"point_code": "p001", "supermarket_oid": 3, "supermarket_name": "Store C"},
        ],
    )
    write_jsonl(
        point_dir / "category_1_prices.jsonl",
        [
            {
                "point_code": "p001",
                "product_oid": 100,
                "product_name": "Rice",
                "quantity": "1kg",
                "category_id": 1,
                "category_name": "Food",
                "supermarket_oid": 1,
                "price_mop": 10.0,
            },
            {
                "point_code": "p001",
                "product_oid": 100,
                "product_name": "Rice",
                "quantity": "1kg",
                "category_id": 1,
                "category_name": "Food",
                "supermarket_oid": 2,
                "price_mop": 15.0,
            },
            {
                "point_code": "p001",
                "product_oid": 100,
                "product_name": "Rice",
                "quantity": "1kg",
                "category_id": 1,
                "category_name": "Food",
                "supermarket_oid": 3,
                "price_mop": None,
            },
            {
                "point_code": "p001",
                "product_oid": 200,
                "product_name": "Tissue",
                "quantity": "3 pack",
                "category_id": 9,
                "category_name": "Household",
                "supermarket_oid": 1,
                "price_mop": 8.0,
            },
        ],
    )
    return tmp_path


def test_same_product_across_stores_calculates_gap(tmp_path: Path) -> None:
    signals = analyze_point_signals("2026-04-25", "p001", make_fixture(tmp_path))

    gap = signals["largest_price_gap"][0]

    assert gap["product_oid"] == 100
    assert gap["gap_mop"] == 5.0
    assert gap["gap_percent"] == 50.0
    assert gap["min_supermarket_name"] == "Store A"
    assert gap["max_supermarket_name"] == "Store B"


def test_none_price_is_ignored_for_price_signals(tmp_path: Path) -> None:
    signals = analyze_point_signals("2026-04-25", "p001", make_fixture(tmp_path))

    rice = next(item for item in signals["cheapest_products_by_keyword"] if item["product_oid"] == 100)

    assert rice["min_price_mop"] == 10.0
    assert all(item["max_supermarket_oid"] != 3 for item in signals["largest_price_gap"])


def test_store_count_coverage_counts_price_records(tmp_path: Path) -> None:
    signals = analyze_point_signals("2026-04-25", "p001", make_fixture(tmp_path))

    coverage = {item["supermarket_oid"]: item for item in signals["store_count_coverage"]}

    assert coverage[1]["price_records"] == 2
    assert coverage[2]["price_records"] == 1
    assert coverage[3]["price_records"] == 1
