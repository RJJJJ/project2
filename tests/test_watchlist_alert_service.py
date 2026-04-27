from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.historical_price_signal_analyzer import NOT_ENOUGH_HISTORY_WARNING
from services.watchlist_alert_service import generate_watchlist_alerts


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
    write_jsonl(point_dir / "supermarkets.jsonl", [{"supermarket_oid": 1, "supermarket_name": "Store A"}])
    write_jsonl(point_dir / "category_1_prices.jsonl", rows)


def test_near_historical_low_generates_medium_alert(tmp_path: Path) -> None:
    write_day(tmp_path, "2026-04-25", [row(100, 10.0, "Rice")])
    write_day(tmp_path, "2026-04-27", [row(100, 10.2, "Rice")])

    result = generate_watchlist_alerts("p001", [{"product_oid": 100, "product_name": "Rice"}], "2026-04-27", processed_root=tmp_path)

    assert result["alerts"][0]["alert_type"] == "near_historical_low"
    assert result["alerts"][0]["severity"] == "medium"
    assert result["alerts"][0]["should_notify"] is True


def test_below_average_discount_over_twenty_generates_high_alert(tmp_path: Path) -> None:
    write_day(tmp_path, "2026-04-25", [row(100, 10.0)])
    write_day(tmp_path, "2026-04-26", [row(100, 100.0)])
    write_day(tmp_path, "2026-04-27", [row(100, 40.0)])

    result = generate_watchlist_alerts("p001", [{"product_oid": 100}], "2026-04-27", processed_root=tmp_path)

    assert result["alerts"][0]["alert_type"] == "below_average"
    assert result["alerts"][0]["severity"] == "high"
    assert result["alerts"][0]["discount_vs_avg_percent"] >= 20


def test_unusual_high_generates_low_non_notify_alert(tmp_path: Path) -> None:
    write_day(tmp_path, "2026-04-25", [row(100, 10.0)])
    write_day(tmp_path, "2026-04-27", [row(100, 20.0)])

    result = generate_watchlist_alerts("p001", [{"product_oid": 100}], "2026-04-27", processed_root=tmp_path)

    assert result["alerts"][0]["alert_type"] == "unusual_high"
    assert result["alerts"][0]["severity"] == "low"
    assert result["alerts"][0]["should_notify"] is False


def test_insufficient_history_generates_no_alert_and_warning(tmp_path: Path) -> None:
    write_day(tmp_path, "2026-04-27", [row(100, 10.0)])

    result = generate_watchlist_alerts("p001", [{"product_oid": 100}], "2026-04-27", processed_root=tmp_path)

    assert result["alerts"] == []
    assert NOT_ENOUGH_HISTORY_WARNING in result["warnings"]
    assert result["item_warnings"][0]["warnings"] == [NOT_ENOUGH_HISTORY_WARNING]


def test_missing_current_price_generates_no_alert_and_item_warning(tmp_path: Path) -> None:
    write_day(tmp_path, "2026-04-27", [row(100, 10.0)])

    result = generate_watchlist_alerts("p001", [{"product_oid": 404}], "2026-04-27", processed_root=tmp_path)

    assert result["alerts"] == []
    assert result["item_warnings"][0]["product_oid"] == 404
    assert result["item_warnings"][0]["warnings"]


def test_empty_items_return_empty_alerts(tmp_path: Path) -> None:
    result = generate_watchlist_alerts("p001", [], "latest", processed_root=tmp_path)

    assert result["alerts"] == []
    assert result["summary"]["items_count"] == 0
    assert result["summary"]["alerts_count"] == 0
