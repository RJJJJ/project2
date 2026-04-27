from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.historical_price_signal_analyzer import NOT_ENOUGH_HISTORY_WARNING
from services.watchlist_signal_service import analyze_watchlist_items


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def row(product_oid: int, price: float, name: str | None = None, supermarket_oid: int = 1) -> dict[str, Any]:
    return {
        "point_code": "p001",
        "product_oid": product_oid,
        "product_name": name or f"Product {product_oid}",
        "quantity": "1kg",
        "category_id": 1,
        "category_name": "Food",
        "supermarket_oid": supermarket_oid,
        "price_mop": price,
    }


def write_day(root: Path, date: str, rows: list[dict[str, Any]], point_code: str = "p001") -> None:
    point_dir = root / date / point_code
    write_jsonl(
        point_dir / "supermarkets.jsonl",
        [
            {"point_code": point_code, "supermarket_oid": 1, "supermarket_name": "Store A"},
            {"point_code": point_code, "supermarket_oid": 2, "supermarket_name": "Store B"},
        ],
    )
    write_jsonl(point_dir / "category_1_prices.jsonl", rows)


def test_current_price_is_returned_when_product_exists(tmp_path: Path) -> None:
    write_day(tmp_path, "2026-04-27", [row(100, 12.0), row(100, 10.0, supermarket_oid=2)])

    result = analyze_watchlist_items(
        "p001",
        [{"product_oid": 100, "product_name": "Rice"}],
        date="2026-04-27",
        processed_root=tmp_path,
    )

    item = result["items"][0]
    assert item["current_min_price_mop"] == 10.0
    assert item["current_store_name"] == "Store B"


def test_missing_current_price_returns_item_warning(tmp_path: Path) -> None:
    write_day(tmp_path, "2026-04-27", [row(100, 10.0)])

    result = analyze_watchlist_items(
        "p001",
        [{"product_oid": 404, "product_name": "Missing"}],
        date="2026-04-27",
        processed_root=tmp_path,
    )

    assert result["items"][0]["current_min_price_mop"] is None
    assert result["items"][0]["warnings"] == ["今日無價格資料。"]


def test_insufficient_history_returns_warning_with_current_price(tmp_path: Path) -> None:
    write_day(tmp_path, "2026-04-27", [row(100, 10.0)])

    result = analyze_watchlist_items(
        "p001",
        [{"product_oid": 100, "product_name": "Rice"}],
        date="2026-04-27",
        processed_root=tmp_path,
    )

    assert NOT_ENOUGH_HISTORY_WARNING in result["warnings"]
    assert NOT_ENOUGH_HISTORY_WARNING in result["items"][0]["warnings"]
    assert result["items"][0]["current_min_price_mop"] == 10.0


def test_historical_data_can_generate_signal_type(tmp_path: Path) -> None:
    write_day(tmp_path, "2026-04-25", [row(100, 10.0)])
    write_day(tmp_path, "2026-04-27", [row(100, 10.2)])

    result = analyze_watchlist_items(
        "p001",
        [{"product_oid": 100, "product_name": "Rice"}],
        date="2026-04-27",
        processed_root=tmp_path,
    )

    assert result["items"][0]["signal_type"] == "near_historical_low"
    assert result["items"][0]["historical_min_price_mop"] == 10.0


def test_multiple_watchlist_items_are_analyzed_together(tmp_path: Path) -> None:
    write_day(tmp_path, "2026-04-25", [row(100, 10.0), row(200, 20.0)])
    write_day(tmp_path, "2026-04-27", [row(100, 10.2), row(200, 30.0)])

    result = analyze_watchlist_items(
        "p001",
        [{"product_oid": 100, "product_name": "Rice"}, {"product_oid": 200, "product_name": "Tissue"}],
        date="2026-04-27",
        processed_root=tmp_path,
    )

    assert [item["product_oid"] for item in result["items"]] == [100, 200]
    assert result["items"][0]["signal_type"] == "near_historical_low"
    assert result["items"][1]["current_min_price_mop"] == 30.0
