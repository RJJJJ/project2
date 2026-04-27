from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.historical_price_signal_analyzer import (
    NOT_ENOUGH_HISTORY_WARNING,
    analyze_historical_price_signals,
)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


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


def signal_for(result: dict[str, Any], product_oid: int) -> dict[str, Any]:
    return next(item for item in result["signals"] if item["product_oid"] == product_oid)


def test_one_date_returns_warning_without_signals(tmp_path: Path) -> None:
    write_day(tmp_path, "2026-04-27", [row(100, 10.0)])

    result = analyze_historical_price_signals("p001", "latest", processed_root=tmp_path)

    assert result["signals"] == []
    assert NOT_ENOUGH_HISTORY_WARNING in result["warnings"]


def test_current_price_near_historical_low(tmp_path: Path) -> None:
    write_day(tmp_path, "2026-04-25", [row(100, 10.0)])
    write_day(tmp_path, "2026-04-27", [row(100, 10.2)])

    result = analyze_historical_price_signals("p001", "2026-04-27", processed_root=tmp_path)

    signal = signal_for(result, 100)
    assert signal["signal_type"] == "near_historical_low"
    assert signal["historical_min_price_mop"] == 10.0
    assert signal["current_min_price_mop"] == 10.2


def test_current_price_below_average_by_ten_percent(tmp_path: Path) -> None:
    write_day(tmp_path, "2026-04-25", [row(100, 10.0)])
    write_day(tmp_path, "2026-04-26", [row(100, 50.0)])
    write_day(tmp_path, "2026-04-27", [row(100, 25.0)])

    result = analyze_historical_price_signals("p001", "2026-04-27", processed_root=tmp_path)

    signal = signal_for(result, 100)
    assert signal["signal_type"] == "below_average"
    assert signal["discount_vs_avg_percent"] == 11.76


def test_current_price_unusual_high(tmp_path: Path) -> None:
    write_day(tmp_path, "2026-04-25", [row(100, 10.0)])
    write_day(tmp_path, "2026-04-27", [row(100, 20.0)])

    result = analyze_historical_price_signals("p001", "2026-04-27", processed_root=tmp_path)

    signal = signal_for(result, 100)
    assert signal["signal_type"] == "unusual_high"
    assert signal["discount_vs_avg_percent"] == -33.33


def test_top_n_limits_sorted_signals(tmp_path: Path) -> None:
    write_day(tmp_path, "2026-04-25", [row(index, 20.0 + index) for index in range(5)])
    write_day(tmp_path, "2026-04-27", [row(index, 10.0) for index in range(5)])

    result = analyze_historical_price_signals("p001", "2026-04-27", top_n=2, processed_root=tmp_path)

    assert len(result["signals"]) == 2
    assert result["summary"]["signals_count"] == 2


def test_one_signal_per_product_uses_highest_priority(tmp_path: Path) -> None:
    write_day(tmp_path, "2026-04-25", [row(100, 10.0)])
    write_day(tmp_path, "2026-04-26", [row(100, 100.0)])
    write_day(tmp_path, "2026-04-27", [row(100, 10.0)])

    result = analyze_historical_price_signals("p001", "2026-04-27", processed_root=tmp_path)

    assert [item["product_oid"] for item in result["signals"]].count(100) == 1
    assert signal_for(result, 100)["signal_type"] == "near_historical_low"


def test_confidence_scales_with_history_dates(tmp_path: Path) -> None:
    for day in range(1, 8):
        write_day(tmp_path, f"2026-04-{day:02d}", [row(100, 10.0 + day)])
    write_day(tmp_path, "2026-04-08", [row(100, 10.0)])

    result = analyze_historical_price_signals("p001", "2026-04-08", processed_root=tmp_path)

    assert signal_for(result, 100)["confidence"] == "high"
