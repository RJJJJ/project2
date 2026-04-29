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


def test_rag_assisted_retrieve_candidates_keeps_not_covered_queries_empty():
    assert rag_assisted_retrieve_candidates(PRODUCTS, "\u96de\u86cb", intent_id=None) == []
    assert rag_assisted_retrieve_candidates(PRODUCTS, "\u85af\u689d", intent_id=None) == []
    assert rag_assisted_retrieve_candidates(PRODUCTS, "M&M", intent_id=None) == []
