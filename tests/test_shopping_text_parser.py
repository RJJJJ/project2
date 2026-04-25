from __future__ import annotations

from services.shopping_text_parser import parse_shopping_text


def test_parse_chinese_quantities_and_classifiers() -> None:
    assert parse_shopping_text("一包米、兩支洗頭水、一包紙巾") == [
        {"keyword": "米", "quantity": 1},
        {"keyword": "洗頭水", "quantity": 2},
        {"keyword": "紙巾", "quantity": 1},
    ]


def test_parse_arabic_quantity() -> None:
    assert parse_shopping_text("2支洗頭水") == [
        {"keyword": "洗頭水", "quantity": 2},
    ]


def test_default_quantity_for_separated_items() -> None:
    assert parse_shopping_text("米、洗頭水、紙巾") == [
        {"keyword": "米", "quantity": 1},
        {"keyword": "洗頭水", "quantity": 1},
        {"keyword": "紙巾", "quantity": 1},
    ]


def test_default_quantity_in_sentence() -> None:
    assert parse_shopping_text("我想買米和洗頭水") == [
        {"keyword": "米", "quantity": 1},
        {"keyword": "洗頭水", "quantity": 1},
    ]
