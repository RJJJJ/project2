from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bot.telegram_bot import render_check_message


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def make_processed_fixture(tmp_path: Path) -> Path:
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
            {
                "point_code": "p001",
                "product_oid": 100,
                "product_name": "香米",
                "quantity": "1公斤",
                "category_id": 1,
                "category_name": "米",
                "supermarket_oid": 1,
                "price_mop": 12.0,
            },
            {
                "point_code": "p001",
                "product_oid": 100,
                "product_name": "香米",
                "quantity": "1公斤",
                "category_id": 1,
                "category_name": "米",
                "supermarket_oid": 2,
                "price_mop": 10.0,
            },
        ],
    )
    return tmp_path


def test_check_message_text_is_not_empty(tmp_path: Path) -> None:
    message = render_check_message(
        "我想買一包米",
        date_setting="2026-04-25",
        default_point_code="p001",
        processed_root=make_processed_fixture(tmp_path),
    )

    assert message.strip()
    assert "cheapest" in message


def test_check_message_has_clear_error_when_processed_data_missing(tmp_path: Path) -> None:
    message = render_check_message(
        "我想買一包米",
        date_setting="2026-04-25",
        default_point_code="p001",
        processed_root=tmp_path,
    )

    assert "找不到 processed data" in message
    assert "date=2026-04-25" in message
    assert "point_code=p001" in message
