from __future__ import annotations

from services.plan_recommender import recommend_plan


def test_recommend_single_store_when_only_slightly_more_expensive() -> None:
    result = recommend_plan(
        [
            {"plan_type": "cheapest_by_item", "estimated_total_mop": 100.0},
            {"plan_type": "cheapest_single_store", "estimated_total_mop": 101.0},
            {"plan_type": "cheapest_two_stores", "estimated_total_mop": 100.0},
        ],
        convenience_threshold_mop=5.0,
    )

    assert result["recommended_plan_type"] == "cheapest_single_store"
    assert result["recommendation_reason"] == "只比最低價方案貴 1.0 MOP，但只需去一間店。"


def test_recommend_two_stores_when_single_store_exceeds_threshold() -> None:
    result = recommend_plan(
        [
            {"plan_type": "cheapest_by_item", "estimated_total_mop": 100.0},
            {"plan_type": "cheapest_single_store", "estimated_total_mop": 110.0},
            {"plan_type": "cheapest_two_stores", "estimated_total_mop": 102.0},
        ],
        convenience_threshold_mop=5.0,
    )

    assert result["recommended_plan_type"] == "cheapest_two_stores"
    assert result["recommendation_reason"] == "在最多兩間店限制下取得最低總價。"


def test_fallback_to_cheapest_by_item_when_two_stores_unavailable() -> None:
    result = recommend_plan(
        [
            {"plan_type": "cheapest_by_item", "estimated_total_mop": 100.0},
            {"plan_type": "cheapest_single_store", "estimated_total_mop": None},
            {"plan_type": "cheapest_two_stores", "estimated_total_mop": None},
        ]
    )

    assert result["recommended_plan_type"] == "cheapest_by_item"
    assert result["recommendation_reason"] == "只能按單品最低價提供參考方案。"
