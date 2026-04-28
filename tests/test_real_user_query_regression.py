from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
testclient = pytest.importorskip("fastapi.testclient")
TestClient = testclient.TestClient

import app.api as api
from app.main import app
from services.product_matching_rules import candidate_text_match_score, is_forbidden_match
from services.simple_basket_parser import parse_simple_basket_text

client = TestClient(app)

FORBIDDEN_RICE = ["米粉", "玉米", "粟米", "米餅", "米線"]


def test_real_user_query_parser_case_1():
    items = {item["keyword"]: item for item in parse_simple_basket_text("兩包麵 一包薯條 四包薯片 油 糖 M&M")}
    assert len(items) >= 6
    assert items["麵"]["quantity"] == 2
    assert items["薯條"]["quantity"] == 1
    assert items["薯片"]["quantity"] == 4
    assert items["油"]["quantity"] == 1
    assert items["糖"]["quantity"] == 1
    assert items["M&M"]["quantity"] == 1


def test_api_partial_plan_not_500(monkeypatch):
    monkeypatch.setattr(api, "is_sqlite_provider_enabled", lambda: False)
    monkeypatch.setattr(api, "get_processed_root", lambda: Path("processed"))
    monkeypatch.setattr(api, "resolve_date", lambda date, processed_root=None: "2026-04-28")
    monkeypatch.setattr(api, "resolve_point_from_request", lambda *args, **kwargs: {"point_code": "p001"})
    monkeypatch.setattr(api, "ensure_processed_data_exists", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        api,
        "build_result",
        lambda *args, **kwargs: {
            "date": "2026-04-28",
            "point_code": "p001",
            "parsed_items": parse_simple_basket_text("兩包麵 一包薯條 四包薯片 油 糖 M&M"),
            "plans": [{"plan_type": "partial_best_effort", "items": [{"keyword": "油"}], "matched_items": [{"keyword": "油"}], "unmatched_items": [{"keyword": "M&M"}], "is_partial": True, "estimated_total_mop": 10, "store_count": 1, "stores": []}],
            "warnings": ["部分商品暫時未能在資料中找到，已先列出找到商品的參考價格。"],
            "recommended_plan_type": "partial_best_effort",
            "recommendation_reason": "部分商品暫時未能匹配。",
        },
    )
    response = client.post("/api/basket/ask", json={"text": "兩包麵 一包薯條 四包薯片 油 糖 M&M", "point_code": "p001"})
    assert response.status_code == 200
    assert response.json()["plans"][0]["is_partial"] is True


def test_rice_forbidden_terms_score_lower():
    good = candidate_text_match_score("米", "青靈芝香米", "5公斤", "米類")
    for bad in FORBIDDEN_RICE:
        assert is_forbidden_match("米", bad, "")
        assert candidate_text_match_score("米", bad, "55克", "穀類食品") < good


def test_rice_noodle_allowed_for_rice_noodle_keyword():
    assert not is_forbidden_match("米粉", "媽媽快熟清湯米粉", "穀類食品")
    assert candidate_text_match_score("米粉", "媽媽快熟清湯米粉", "55克", "穀類食品") > 0


def test_chips_and_fries_separate():
    assert is_forbidden_match("薯片", "冷凍薯條", "")
    assert is_forbidden_match("薯條", "樂事薯片", "")
    assert candidate_text_match_score("薯片", "樂事薯片", "", "") > candidate_text_match_score("薯片", "冷凍薯條", "", "")


def test_oil_and_sugar_forbidden_matches():
    assert is_forbidden_match("油", "護髮油", "個人護理")
    assert is_forbidden_match("糖", "朱古力糖果", "零食")
    assert candidate_text_match_score("油", "花生食油", "900ml", "食油") > candidate_text_match_score("油", "護髮油", "", "")
    assert candidate_text_match_score("糖", "白砂糖", "1公斤", "調味") > candidate_text_match_score("糖", "糖果", "", "")


def test_m_and_m_graceful():
    assert parse_simple_basket_text("M&M")[0]["keyword"] == "M&M"
    assert candidate_text_match_score("M&M", "朱古力豆", "", "零食") > 0


def test_mixed_household_rules():
    items = [item["keyword"] for item in parse_simple_basket_text("米 洗頭水 紙巾")]
    assert items == ["米", "洗頭水", "紙巾"]
    assert is_forbidden_match("洗頭水", "沐浴露", "")
    assert is_forbidden_match("紙巾", "消毒濕紙巾", "")


def test_garbage_query_no_crash():
    assert parse_simple_basket_text("???") == []
