from services.product_intent_resolver import resolve_product_intent


def test_sugar_is_ambiguous():
    assert resolve_product_intent("糖")["status"] == "ambiguous"


def test_granulated_sugar_is_cooking_sugar():
    result = resolve_product_intent("砂糖")
    assert result["status"] == "covered"
    assert result["intent_id"] == "cooking_sugar"


def test_oil_is_ambiguous_but_cooking_oil_is_covered():
    assert resolve_product_intent("油")["status"] == "ambiguous"
    result = resolve_product_intent("食油")
    assert result["status"] == "covered"
    assert result["intent_id"] == "cooking_oil"


def test_shampoo_synonym_is_covered():
    result = resolve_product_intent("洗頭水")
    assert result["status"] == "covered"
    assert result["intent_id"] == "shampoo"


def test_explicit_not_covered_queries():
    for query in ["M&M", "薯條", "雞蛋", "鮮蛋"]:
        result = resolve_product_intent(query)
        assert result["status"] == "not_covered"


def test_chocolate_and_tissue_ambiguity_and_specific_forms():
    assert resolve_product_intent("朱古力")["status"] == "ambiguous"
    drink = resolve_product_intent("朱古力飲品")
    assert drink["status"] == "covered"
    assert drink["intent_id"] == "chocolate_drink"
    assert resolve_product_intent("紙巾")["status"] == "ambiguous"
    wet = resolve_product_intent("濕紙巾")
    assert wet["status"] == "covered"
    assert wet["intent_id"] == "wet_wipe"
