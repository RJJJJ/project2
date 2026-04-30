from services.query_intent_router import route_user_query


def test_route_brand_search():
    result = route_user_query("出前一丁")
    assert result["query_type"] == "brand_search"
    assert result["confidence"] == "high"
    assert result["items"][0]["brand"] == "出前一丁"


def test_route_partial_product_search():
    result = route_user_query("出前一丁麻油味")
    assert result["query_type"] in {"partial_product_search", "direct_product_search"}


def test_route_direct_product_search():
    result = route_user_query("麥老大雞蛋幼面")
    assert result["query_type"] == "direct_product_search"


def test_route_not_covered_and_ambiguous():
    assert route_user_query("雞蛋")["query_type"] == "not_covered_request"
    assert route_user_query("麵")["query_type"] == "ambiguous_request"
    assert route_user_query("面")["query_type"] == "ambiguous_request"


def test_route_subjective_recommendation():
    result = route_user_query("最好吃的麵")
    assert result["query_type"] == "subjective_recommendation"
    assert result["confidence"] == "high"


def test_route_cheapest_brand_goal():
    result = route_user_query("最便宜的出前一丁")
    assert result["query_type"] == "brand_search"
    assert result["items"][0]["goal"] == "cheapest"
