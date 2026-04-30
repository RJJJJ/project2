from services.product_direct_search import search_direct_products, should_try_direct_product_search


PRODUCTS = [
    {"product_oid": "20", "product_name": "出前一丁麻油味即食麵(袋裝)", "category_id": 2, "category_name": "穀類食品", "package_quantity": "100克"},
    {"product_oid": "667", "product_name": "出前一丁九州濃湯豬骨湯味即食麵", "category_id": 2, "category_name": "穀類食品", "package_quantity": "100克"},
    {"product_oid": "843", "product_name": "麥老大雞蛋幼面", "category_id": 2, "category_name": "穀類食品", "package_quantity": "920克"},
]


def test_direct_search_flavor_ranks_before_other_flavor():
    result = search_direct_products(PRODUCTS, "出前一丁麻油味")
    assert result["confidence"] == "high"
    assert result["matches"][0]["product_name"] == "出前一丁麻油味即食麵(袋裝)"
    assert "九州" not in result["matches"][0]["product_name"]


def test_direct_search_specific_product():
    result = search_direct_products(PRODUCTS, "麥老大雞蛋幼面")
    assert result["matches"][0]["product_name"] == "麥老大雞蛋幼面"


def test_direct_search_short_high_risk_disabled():
    assert should_try_direct_product_search("糖") is False
    result = search_direct_products(PRODUCTS, "糖")
    assert result["status"] == "no_match"
    assert result["risky"] is True
