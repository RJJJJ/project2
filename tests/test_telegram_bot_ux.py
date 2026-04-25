from __future__ import annotations

from bot.telegram_bot import DEFAULT_POINT_CODE, parse_check_args
from scripts.generate_point_signals import format_signals_text
from services.telegram_message_utils import split_long_message


def test_split_long_message() -> None:
    text = "alpha\n\n" + "b" * 12 + "\n" + "c" * 12 + "\n\nomega"

    parts = split_long_message(text, max_len=10)

    assert all(len(part) <= 10 for part in parts)
    assert "".join(parts) == text
    assert parts[0] == "alpha\n\n"


def test_parse_check_args_with_point_code() -> None:
    point_code, shopping_text = parse_check_args(["p001", "我想買一包米、兩支洗頭水"])

    assert point_code == "p001"
    assert shopping_text == "我想買一包米、兩支洗頭水"


def test_parse_check_args_without_point_code() -> None:
    point_code, shopping_text = parse_check_args(["我想買一包米"])

    assert point_code == DEFAULT_POINT_CODE
    assert shopping_text == "我想買一包米"


def test_signals_top_n_formatting() -> None:
    signals = {
        "date": "2026-04-25",
        "point_code": "p001",
        "largest_price_gap": [
            {
                "product_name": f"product-{index}",
                "quantity": "1件",
                "min_price_mop": 1,
                "max_price_mop": 2,
                "gap_percent": 100,
                "min_supermarket_name": "A",
                "max_supermarket_name": "B",
            }
            for index in range(1, 8)
        ],
    }

    default_text = format_signals_text(signals)
    top_ten_text = format_signals_text(signals, top_n=10)

    assert "product-5" in default_text
    assert "product-6" not in default_text
    assert "product-7" not in default_text
    assert "product-7" in top_ten_text
