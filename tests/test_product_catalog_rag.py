from services.product_catalog_rag import build_product_catalog_documents, rag_assisted_retrieve_candidates


PRODUCTS = [
    {"product_oid": "1", "product_name": "\u6f58\u5a77\u6d17\u9aee\u9732", "category_id": 10, "category_name": "\u500b\u4eba\u8b77\u7406", "package_quantity": "500ml"},
    {"product_oid": "2", "product_name": "\u4f4e\u7cd6\u8c46\u5976", "category_id": 6, "category_name": "\u98f2\u54c1", "package_quantity": "1L"},
    {"product_oid": "3", "product_name": "\u592a\u53e4\u7d14\u6b63\u7802\u7cd6", "category_id": 5, "category_name": "\u7cd6", "package_quantity": "1kg"},
    {"product_oid": "4", "product_name": "\u96de\u86cb\u5e7c\u9eb5", "category_id": 2, "category_name": "\u9eb5", "package_quantity": "5\u5305"},
    {"product_oid": "5", "product_name": "\u91d1\u9f8d\u9b5a\u82b1\u751f\u6cb9", "category_id": 3, "category_name": "\u98df\u6cb9", "package_quantity": "1L"},
    {"product_oid": "6", "product_name": "\u9ebb\u6cb9\u5473\u5373\u98df\u9eb5", "category_id": 2, "category_name": "\u9eb5", "package_quantity": "1\u5305"},
]


def test_build_product_catalog_documents_contains_search_text():
    documents = build_product_catalog_documents(PRODUCTS)
    assert documents[0]["product_oid"] == "1"
    assert "\u6f58\u5a77\u6d17\u9aee\u9732" in documents[0]["search_text"]


def test_rag_assisted_retrieve_candidates_finds_shampoo():
    names = [item["product_name"] for item in rag_assisted_retrieve_candidates(PRODUCTS, "\u6d17\u982d\u6c34", intent_id="shampoo")]
    assert names[:1] == ["\u6f58\u5a77\u6d17\u9aee\u9732"]


def test_rag_assisted_retrieve_candidates_avoids_wrong_oil_candidate():
    names = [item["product_name"] for item in rag_assisted_retrieve_candidates(PRODUCTS, "\u98df\u6cb9", intent_id="cooking_oil")]
    assert "\u91d1\u9f8d\u9b5a\u82b1\u751f\u6cb9" in names
    assert "\u9ebb\u6cb9\u5473\u5373\u98df\u9eb5" not in names


def test_rag_assisted_retrieve_candidates_avoids_low_sugar_soy_milk_for_sugar():
    names = [item["product_name"] for item in rag_assisted_retrieve_candidates(PRODUCTS, "\u7802\u7cd6", intent_id="cooking_sugar")]
    assert names == ["\u592a\u53e4\u7d14\u6b63\u7802\u7cd6"]


def test_cooking_sugar_requires_intent_match_not_category_only():
    products = [
        {"product_oid": "sugar", "product_name": "\u592a\u53e4\u7d14\u6b63\u7802\u7cd6", "category_id": 5},
        {"product_oid": "soy", "product_name": "\u7dad\u4ed6\u5976\u4f4e\u7cd6\u8c46\u5976", "category_id": 6},
        {"product_oid": "gochujang", "product_name": "CJ\u597d\u9910\u5f97\u97d3\u5f0f\u8fa3\u6912\u91ac", "category_id": 5},
        {"product_oid": "vinegar", "product_name": "\u516b\u73cd\u751c\u918b", "category_id": 5},
    ]
    names = [item["product_name"] for item in rag_assisted_retrieve_candidates(products, "\u7802\u7cd6", intent_id="cooking_sugar")]
    assert "\u592a\u53e4\u7d14\u6b63\u7802\u7cd6" in names
    assert "\u7dad\u4ed6\u5976\u4f4e\u7cd6\u8c46\u5976" not in names
    assert "CJ\u597d\u9910\u5f97\u97d3\u5f0f\u8fa3\u6912\u91ac" not in names
    assert "\u516b\u73cd\u751c\u918b" not in names


def test_cooking_oil_requires_oil_match_not_sauce_or_noodle_flavor():
    products = [
        {"product_oid": "oil", "product_name": "\u5200\u561c\u7d14\u6b63\u82b1\u751f\u6cb9", "category_id": 3},
        {"product_oid": "noodle", "product_name": "\u51fa\u524d\u4e00\u4e01\u9ebb\u6cb9\u5473\u5373\u98df\u9eb5", "category_id": 2},
        {"product_oid": "oyster", "product_name": "\u674e\u9326\u8a18\u8814\u6cb9", "category_id": 5},
    ]
    names = [item["product_name"] for item in rag_assisted_retrieve_candidates(products, "\u98df\u6cb9", intent_id="cooking_oil")]
    assert "\u5200\u561c\u7d14\u6b63\u82b1\u751f\u6cb9" in names
    assert "\u51fa\u524d\u4e00\u4e01\u9ebb\u6cb9\u5473\u5373\u98df\u9eb5" not in names
    assert "\u674e\u9326\u8a18\u8814\u6cb9" not in names


def test_shampoo_requires_hair_wash_match_not_same_category_body_wash():
    products = [
        {"product_oid": "shampoo", "product_name": "\u591a\u82ac\u6df1\u5c64\u4fee\u8b77\u6d17\u9aee\u4e73", "category_id": 10},
        {"product_oid": "bodywash", "product_name": "\u591a\u82ac\u6c90\u6d74\u9732", "category_id": 10},
    ]
    names = [item["product_name"] for item in rag_assisted_retrieve_candidates(products, "\u6d17\u982d\u6c34", intent_id="shampoo")]
    assert "\u591a\u82ac\u6df1\u5c64\u4fee\u8b77\u6d17\u9aee\u4e73" in names
    assert "\u591a\u82ac\u6c90\u6d74\u9732" not in names


def test_rag_assisted_retrieve_candidates_keeps_not_covered_queries_empty():
    assert rag_assisted_retrieve_candidates(PRODUCTS, "\u96de\u86cb", intent_id=None) == []
    assert rag_assisted_retrieve_candidates(PRODUCTS, "\u85af\u689d", intent_id=None) == []
    assert rag_assisted_retrieve_candidates(PRODUCTS, "M&M", intent_id=None) == []
