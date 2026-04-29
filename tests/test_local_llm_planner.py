from services.local_llm_planner import (
    normalize_planner_items,
    plan_query_with_rule_fallback,
    validate_planner_output,
)


def test_validate_planner_output_accepts_valid_schema():
    payload = {
        "task_type": "basket_price_optimization",
        "language": "zh-HK",
        "items": [{"raw": "\u7c73", "quantity": 1, "unit": "\u5305", "notes": None}],
        "optimization_goal": "cheapest",
        "location_hint": None,
        "confidence": "medium",
        "warnings": [],
    }
    assert validate_planner_output(payload) == (True, [])


def test_validate_planner_output_rejects_missing_items():
    ok, errors = validate_planner_output(
        {
            "task_type": "basket_price_optimization",
            "language": "zh-HK",
            "items": [],
            "optimization_goal": "cheapest",
            "location_hint": None,
            "confidence": "medium",
            "warnings": [],
        }
    )
    assert ok is False
    assert "items must be a non-empty list" in errors


def test_rule_fallback_extracts_hk_query_shape():
    payload = plan_query_with_rule_fallback(
        "\u4eca\u665a\u6253\u908a\u7210\uff0c\u60f3\u8cb7\u5e7e\u652f\u98f2\u54c1\u3001\u7d19\u5dfe\u540c\u4e00\u5305\u7c73\uff0c\u6700\u597d\u5e73\u5572"
    )
    assert payload["language"] == "zh-HK"
    assert payload["confidence"] in {"medium", "high"}
    assert payload["warnings"] == ["\u5e7e\u652f interpreted as 3"]
    assert payload["items"] == [
        {"raw": "\u98f2\u54c1", "quantity": 3, "unit": "\u652f", "notes": "\u5e7e\u652f interpreted as 3"},
        {"raw": "\u7d19\u5dfe", "quantity": 1, "unit": None, "notes": None},
        {"raw": "\u7c73", "quantity": 1, "unit": "\u5305", "notes": None},
    ]


def test_normalize_planner_items_defaults_missing_fields():
    normalized = normalize_planner_items(
        {
            "language": "bad",
            "items": [{"raw": "\u7802\u7cd6", "quantity": 0, "unit": "", "notes": "  "}],
            "optimization_goal": "bad",
            "confidence": "bad",
            "warnings": ["x", ""],
        }
    )
    assert normalized["language"] == "mixed"
    assert normalized["optimization_goal"] == "unknown"
    assert normalized["confidence"] == "low"
    assert normalized["items"] == [{"raw": "\u7802\u7cd6", "quantity": 1, "unit": None, "notes": None}]
    assert normalized["warnings"] == ["x"]
