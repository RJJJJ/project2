from services.product_catalog_rag_v2 import rag_v2_retrieve_candidates


PRODUCTS = [
    {"product_oid": "1", "product_name": "出前一丁麻油味即食麵(袋裝)", "category_name": "穀類食品", "category_id": 2, "package_quantity": "100克"},
    {"product_oid": "2", "product_name": "出前一丁九州濃湯豬骨湯味即食麵", "category_name": "穀類食品", "category_id": 2, "package_quantity": "100克"},
    {"product_oid": "3", "product_name": "維他奶低糖豆奶", "category_name": "飲品", "category_id": 9, "package_quantity": "250毫升"},
    {"product_oid": "4", "product_name": "太古純正砂糖", "category_name": "調味料", "category_id": 5, "package_quantity": "454克"},
    {"product_oid": "5", "product_name": "麥老大雞蛋幼面", "category_name": "穀類食品", "category_id": 2, "package_quantity": "454克"},
]


def test_rag_v2_flavor_ranks_sesame_above_pork_bone():
    results = rag_v2_retrieve_candidates(PRODUCTS, "出前一丁麻油味", brand="出前一丁")
    assert results[0]["product_name"] == "出前一丁麻油味即食麵(袋裝)"
    assert results[0]["rag_features"]["flavor_match"]


def test_rag_v2_sugar_does_not_return_low_sugar_soy_milk():
    results = rag_v2_retrieve_candidates(PRODUCTS, "砂糖", intent_id=None)
    names = [item["product_name"] for item in results]
    assert "太古純正砂糖" in names
    assert "維他奶低糖豆奶" not in names[:1]


def test_rag_v2_high_risk_egg_without_intent_does_not_return_egg_noodle():
    results = rag_v2_retrieve_candidates(PRODUCTS, "雞蛋", intent_id=None)
    assert results == []


def test_rag_v2_category_allowlist_alone_does_not_qualify_candidate():
    products = [{"product_oid": "x", "product_name": "完全無關商品", "category_name": "穀類食品"}]
    results = rag_v2_retrieve_candidates(products, "陌生詞", intent_id="instant_noodle")
    assert results == []
