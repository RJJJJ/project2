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


def make_rice_fixture(tmp_path: Path) -> Path:
    point_dir = tmp_path / "2026-04-25" / "p001"
    write_jsonl(
        point_dir / "supermarkets.jsonl",
        [
            {"point_code": "p001", "supermarket_oid": 1, "supermarket_name": "Store A"},
            {"point_code": "p001", "supermarket_oid": 2, "supermarket_name": "Store B"},
        ],
    )
    write_jsonl(
        point_dir / "category_1_prices.jsonl",
        [
            {"point_code": "p001", "product_oid": 1, "product_name": "\u4f4e\u50f9\u73cd\u73e0\u7c73", "quantity": "1\u516c\u65a4", "category_id": 1, "category_name": "\u7c73\u985e", "supermarket_oid": 1, "price_mop": 8.0},
            {"point_code": "p001", "product_oid": 2, "product_name": "\u5bb6\u5ead\u88dd\u73cd\u73e0\u7c73", "quantity": "5\u516c\u65a4", "category_id": 1, "category_name": "\u7c73\u985e", "supermarket_oid": 1, "price_mop": 45.0},
            {"point_code": "p001", "product_oid": 2, "product_name": "\u5bb6\u5ead\u88dd\u73cd\u73e0\u7c73", "quantity": "5\u516c\u65a4", "category_id": 1, "category_name": "\u7c73\u985e", "supermarket_oid": 2, "price_mop": 48.0},
        ],
    )
    return tmp_path


def test_rice_package_preference_boosts_common_household_size(tmp_path: Path) -> None:
    processed_root = make_rice_fixture(tmp_path)

    candidates = search_product_candidates("2026-04-25", "p001", "\u7c73", processed_root=processed_root)
    by_oid = {candidate["product_oid"]: candidate for candidate in candidates}

    assert by_oid[2]["ranking_factors"]["package_preference_score"] > by_oid[1]["ranking_factors"]["package_preference_score"]
    assert candidates[0]["product_oid"] == 2
    assert by_oid[2]["ranking_factors"]["final_score"] > by_oid[1]["ranking_factors"]["final_score"]


def test_first_candidate_is_recommended_with_explainable_factors(tmp_path: Path) -> None:
    processed_root = make_rice_fixture(tmp_path)

    candidates = search_product_candidates("2026-04-25", "p001", "\u7c73", processed_root=processed_root)

    assert candidates[0]["is_recommended"] is True
    assert candidates[0]["recommendation_reason"]
    assert all(candidate["is_recommended"] is False for candidate in candidates[1:])
    for key in ("match_score", "coverage_score", "package_preference_score", "price_score", "final_score"):
        assert key in candidates[0]["ranking_factors"]
