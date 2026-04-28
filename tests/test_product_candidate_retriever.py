from services.product_candidate_retriever import retrieve_candidates_by_intent


def test_cooking_sugar_excludes_low_sugar_soy_milk():
    products = [
        {"product_oid": "1", "product_name": "維他奶低糖豆奶", "category_id": 6},
        {"product_oid": "2", "product_name": "太古純正砂糖", "category_id": 5},
    ]
    candidates = retrieve_candidates_by_intent(products, "cooking_sugar")
    assert [item["product_name"] for item in candidates] == ["太古純正砂糖"]


def test_cooking_oil_excludes_noodle_and_oyster_sauce():
    products = [
        {"product_oid": "1", "product_name": "麻油味即食麵", "category_id": 2},
        {"product_oid": "2", "product_name": "蠔油炒麵", "category_id": 2},
        {"product_oid": "3", "product_name": "獅球嘜花生油", "category_id": 3},
    ]
    candidates = retrieve_candidates_by_intent(products, "cooking_oil")
    assert [item["product_name"] for item in candidates] == ["獅球嘜花生油"]


def test_egg_does_not_use_egg_noodle_as_candidate():
    products = [
        {"product_oid": "1", "product_name": "雞蛋幼面", "category_id": 2},
        {"product_oid": "2", "product_name": "全蛋麵", "category_id": 2},
    ]
    assert retrieve_candidates_by_intent(products, "egg") == []


def test_retriever_adds_match_metadata():
    products = [{"product_oid": "1", "product_name": "潔柔盒裝紙巾", "category_id": 15}]
    candidate = retrieve_candidates_by_intent(products, "tissue")[0]
    assert candidate["match_intent_id"] == "tissue"
    assert "紙巾" in candidate["matched_positive_terms"]
