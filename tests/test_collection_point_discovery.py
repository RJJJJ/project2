from __future__ import annotations

import csv
import json
from pathlib import Path

from scripts.build_collection_points_candidate_config import build_candidate_config
from scripts.discover_collection_points_from_browser import dedupe_capture_rows, parse_by_condition_url
from scripts.plan_45_point_expansion import plan_expansion

BY_CONDITION_URL = "https://api03.consumer.gov.mo/ccapi/web/sm/v2/uat/itemsPrice/by_condition?key=&size=0&categories=11&items=&cet=22.211085175932098,113.55130120197178&dst=400&lang=cn"


def test_parse_by_condition_url():
    row = parse_by_condition_url(BY_CONDITION_URL, captured_at="2026-04-28T00:00:00+00:00", source_url="source")

    assert row is not None
    assert row["lat"] == 22.211085175932098
    assert row["lng"] == 113.55130120197178
    assert row["dst"] == 400
    assert row["categories"] == "11"
    assert row["lang"] == "cn"
    assert row["dedupe_key"] == "22.211085175932098,113.55130120197178,400"


def test_non_by_condition_url_returns_none():
    assert parse_by_condition_url("https://api03.consumer.gov.mo/app/supermarket/main") is None


def test_dedupe_captures():
    rows = [
        {"lat": 1.0, "lng": 2.0, "dst": 400, "dedupe_key": "1.0,2.0,400"},
        {"lat": 1.0, "lng": 2.0, "dst": 400, "dedupe_key": "1.0,2.0,400"},
        {"lat": 1.1, "lng": 2.0, "dst": 400, "dedupe_key": "1.1,2.0,400"},
    ]

    assert len(dedupe_capture_rows(rows)) == 2
    marked = dedupe_capture_rows(rows, mark_duplicates=True)
    assert [row["duplicate"] for row in marked] == [False, True, False]


def test_build_candidate_config_with_missing_names():
    rows = [{"lat": 22.1, "lng": 113.5, "dst": 400}]

    candidates, summary = build_candidate_config(rows, existing_points=[])

    assert candidates[0]["point_code"] == "candidate_001"
    assert candidates[0]["name"] == "待命名地點 001"
    assert candidates[0]["district"] == "待確認"
    assert candidates[0]["is_new_candidate"] is True
    assert summary["missing_names_count"] == 1


def test_build_candidate_config_with_names_csv_mapping_shape():
    rows = [{"lat": 22.211085175932098, "lng": 113.55130120197178, "dst": 400}]
    mappings = [
        {
            "point_code": "p016",
            "name": "測試地點",
            "district": "澳門半島",
            "lat": "22.211085175932098",
            "lng": "113.55130120197178",
            "dst": "400",
            "notes": "manual",
        }
    ]

    candidates, summary = build_candidate_config(rows, existing_points=[], name_mappings=mappings)

    assert candidates[0]["point_code"] == "p016"
    assert candidates[0]["name"] == "測試地點"
    assert candidates[0]["district"] == "澳門半島"
    assert summary["missing_names_count"] == 0


def test_plan_candidate_points_less_than_45_ready_false(tmp_path: Path):
    candidate = tmp_path / "candidate.json"
    candidate.write_text(json.dumps([{"point_code": "p001", "name": "A", "lat": 1, "lng": 2, "dst": 400}]), encoding="utf-8")

    summary = plan_expansion(candidate, max_points=45, categories="1-19")

    assert summary["ready_for_fetch"] is False
    assert summary["candidate_points"] == 1
    assert summary["estimated_api_requests"] == 855


def test_plan_candidate_points_45_estimates_requests(tmp_path: Path):
    candidate = tmp_path / "candidate.json"
    points = [
        {"point_code": f"p{i:03d}", "name": f"Point {i}", "district": "澳門", "lat": 22 + i / 1000, "lng": 113, "dst": 400}
        for i in range(1, 46)
    ]
    candidate.write_text(json.dumps(points), encoding="utf-8")

    summary = plan_expansion(candidate, max_points=45, categories="1-19")

    assert summary["ok"] is True
    assert summary["ready_for_fetch"] is True
    assert summary["candidate_points"] == 45
    assert summary["estimated_api_requests"] == 855
    assert summary["dst_values"] == [400]
