from services.simple_basket_parser import extract_location_text, parse_simple_basket_text

TEXT = "\u6211\u5728\u9ad8\u58eb\u5fb7\uff0c\u60f3\u8cb7\u4e00\u5305\u7c73\u3001\u5169\u652f\u6d17\u982d\u6c34\u3001\u4e00\u5305\u7d19\u5dfe"


def test_parse_simple_basket_text_quantities() -> None:
    items = parse_simple_basket_text(TEXT)

    assert items == [
        {"keyword": "\u7c73", "quantity": 1, "unit": "\u5305", "raw_text": "\u60f3\u8cb7\u4e00\u5305\u7c73"},
        {"keyword": "\u6d17\u982d\u6c34", "quantity": 2, "unit": "\u652f", "raw_text": "\u5169\u652f\u6d17\u982d\u6c34"},
        {"keyword": "\u7d19\u5dfe", "quantity": 1, "unit": "\u5305", "raw_text": "\u4e00\u5305\u7d19\u5dfe"},
    ]


def test_parse_comma_separated_keywords_default_quantity() -> None:
    items = parse_simple_basket_text("\u7c73\u3001\u6d17\u982d\u6c34\u3001\u7d19\u5dfe")

    assert [item["keyword"] for item in items] == ["\u7c73", "\u6d17\u982d\u6c34", "\u7d19\u5dfe"]
    assert [item["quantity"] for item in items] == [1, 1, 1]


def test_extract_location_text() -> None:
    assert extract_location_text(TEXT) == "\u9ad8\u58eb\u5fb7"
