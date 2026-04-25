from __future__ import annotations

from services.basket_text_formatter import format_basket_text


def test_text_output_contains_recommendation_total_and_disclaimer() -> None:
    result = {
        "date": "2026-04-25",
        "point_code": "p001",
        "parsed_items": [{"keyword": "米", "quantity": 1}],
        "recommended_plan_type": "cheapest_single_store",
        "recommendation_reason": "只比最低價方案貴 1.0 MOP，但只需去一間店。",
        "plans": [
            {
                "plan_type": "cheapest_by_item",
                "estimated_total_mop": 99.0,
                "stores": [],
                "items": [],
            },
            {
                "plan_type": "cheapest_single_store",
                "estimated_total_mop": 100.0,
                "stores": [{"supermarket_oid": 1, "supermarket_name": "Store A"}],
                "items": [
                    {
                        "product_name": "香米",
                        "package_quantity": "5kg",
                        "requested_quantity": 1,
                        "unit_price_mop": 100.0,
                        "subtotal_mop": 100.0,
                        "supermarket_name": "Store A",
                    }
                ],
            },
            {
                "plan_type": "cheapest_two_stores",
                "estimated_total_mop": 99.0,
                "stores": [],
                "items": [],
            },
        ],
    }

    text = format_basket_text(
        result,
        "我想買一包米",
        {"point_code": "p001", "name": "高士德", "district": "澳門半島"},
    )

    assert "澳門採購決策建議" in text
    assert "推薦方案名稱：cheapest_single_store" in text
    assert "預估總價：100.0 MOP" in text
    assert "價格只供參考，以店內標示為準。" in text
