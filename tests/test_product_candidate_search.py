from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.product_candidate_search import search_product_candidates


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def make_fixture(tmp_path: Path) -> Path:
    point_dir = tmp_path / "2026-04-25" / "p001"
    write_jsonl(
        point_dir / "supermarkets.jsonl",
        [
            {"point_code": "p001", "supermarket_oid": 1, "supermarket_name": "Store A"},
            {"point_code": "p001", "supermarket_oid": 2, "supermarket_name": "Store B"},
            {"point_code": "p001", "supermarket_oid": 3, "supermarket_name": "Store C"},
        ],
    )
    write_jsonl(
        point_dir / "category_1_prices.jsonl",
        [
            {"point_code": "p001", "product_oid": 101, "product_name": "\u5bcc\u58eb\u73cd\u73e0\u7c73", "quantity": "1\u516c\u65a4", "category_id": 1, "category_name": "\u7c73\u985e", "supermarket_oid": 1, "price_mop": 13.5},
            {"point_code": "p001", "product_oid": 101, "product_name": "\u5bcc\u58eb\u73cd\u73e0\u7c73", "quantity": "1\u516c\u65a4", "category_id": 1, "category_name": "\u7c73\u985e", "supermarket_oid": 2, "price_mop": 18.0},
            {"point_code": "p001", "product_oid": 102, "product_name": "\u91d1\u5154\u738b\u9802\u7d1a\u7cef\u7c73", "quantity": "5\u516c\u65a4", "category_id": 1, "category_name": "\u7c73\u985e", "supermarket_oid": 3, "price_mop": 68.0},
            {"point_code": "p001", "product_oid": 103, "product_name": "\u7121\u50f9\u683c\u767d\u7c73", "quantity": "1\u516c\u65a4", "category_id": 1, "category_name": "\u7c73\u985e", "supermarket_oid": 3, "price_mop": None},
        ],
    )
    return tmp_path


def test_keyword_returns_candidates_and_aggregates_by_product_oid(tmp_path: Path) -> None:
    processed_root = make_fixture(tmp_path)

    candidates = search_product_candidates("2026-04-25", "p001", "\u7c73", processed_root=processed_root)

    by_oid = {candidate["product_oid"]: candidate for candidate in candidates}
    aggregated = by_oid[101]
    assert aggregated["matched_alias"] == "\u7c73"
    assert aggregated["min_price_mop"] == 13.5
    assert aggregated["max_price_mop"] == 18.0
    assert aggregated["store_count"] == 2
    assert aggregated["sample_supermarkets"] == ["Store A", "Store B"]
    assert {candidate["product_oid"] for candidate in candidates} == {101, 102}


def test_candidate_keeps_old_fields_and_adds_ranking_fields(tmp_path: Path) -> None:
    processed_root = make_fixture(tmp_path)

    candidate = search_product_candidates("2026-04-25", "p001", "\u7c73", processed_root=processed_root)[0]

    for field in ("product_oid", "product_name", "package_quantity", "min_price_mop", "max_price_mop", "store_count"):
        assert field in candidate
    assert "is_recommended" in candidate
    assert "recommendation_reason" in candidate
    assert "ranking_factors" in candidate
    assert "final_score" in candidate["ranking_factors"]


def test_limit_is_applied_after_ranking(tmp_path: Path) -> None:
    processed_root = make_fixture(tmp_path)

    candidates = search_product_candidates("2026-04-25", "p001", "\u7c73", limit=1, processed_root=processed_root)

    assert len(candidates) == 1
    assert candidates[0]["is_recommended"] is True


def test_no_candidates_returns_empty_list(tmp_path: Path) -> None:
    processed_root = make_fixture(tmp_path)

    assert search_product_candidates("2026-04-25", "p001", "notfound", processed_root=processed_root) == []
