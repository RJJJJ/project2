from services.grounded_answer_formatter import format_grounded_basket_answer


def test_formatter_displays_total_items_and_stores() -> None:
    basket = {
        "date": "2026-04-28",
        "point_code": "p001",
        "items": [
            {"keyword": "\u7c73", "matched": True, "product_name": "\u9999\u7c73", "package_quantity": "5\u516c\u65a4", "unit_price_mop": 69.0, "supermarket_name": "Store A"}
        ],
        "estimated_total_mop": 69.0,
        "warnings": [],
    }

    answer = format_grounded_basket_answer(basket)

    assert "69.0 MOP" in answer["answer_text"]
    assert "Store A" in answer["answer_text"]
    assert answer["facts_used"]["estimated_total_mop"] == 69.0
    assert answer["facts_used"]["stores"] == ["Store A"]


def test_formatter_lists_unmatched_items() -> None:
    basket = {
        "date": "2026-04-28",
        "point_code": "p001",
        "items": [{"keyword": "\u6d17\u982d\u6c34", "quantity": 1, "matched": False}],
        "estimated_total_mop": 0.0,
        "warnings": ["missing"],
    }

    answer = format_grounded_basket_answer(basket)

    assert "\u672a\u80fd\u627e\u5230\u7684\u5546\u54c1" in answer["answer_text"]
    assert "\u6d17\u982d\u6c34" in answer["answer_text"]
    assert answer["warnings"] == ["missing"]


def test_facts_used_core_fields() -> None:
    basket = {"date": "2026-04-28", "point_code": "p001", "items": [], "estimated_total_mop": 0.0, "warnings": []}

    facts = format_grounded_basket_answer(basket)["facts_used"]

    assert set(facts) == {"date", "point_code", "estimated_total_mop", "stores", "items"}
