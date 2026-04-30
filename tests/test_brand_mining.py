from services.brand_mining import build_brand_alias_index, detect_brand_query, extract_brand_candidates_from_products


def _products():
    return [
        {"product_name": "出前一丁麻油味即食麵(袋裝)"},
        {"product_name": "維他奶低糖豆奶"},
        {"product_name": "品客原味薯片"},
        {"product_name": "太古純正砂糖"},
        {"product_name": "即食麵"},
        {"product_name": "牛奶"},
        {"product_name": "砂糖"},
    ]


def test_brand_mining_detects_major_catalog_brands():
    brands = {item["brand"] for item in extract_brand_candidates_from_products(_products())}
    assert {"出前一丁", "維他奶", "品客", "太古"} <= brands


def test_brand_mining_avoids_generic_product_words():
    brands = {item["brand"] for item in extract_brand_candidates_from_products(_products())}
    assert "即食麵" not in brands
    assert "牛奶" not in brands
    assert "砂糖" not in brands


def test_detect_brand_query_uses_alias_index():
    index = build_brand_alias_index(_products())
    result = detect_brand_query("出前一丁", index)
    assert result["matched"]
    assert result["brand"] == "出前一丁"
