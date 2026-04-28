from __future__ import annotations

import json
from pathlib import Path

from scripts.generate_coverage_report import build_coverage_report, render_markdown


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")


def _point(code: str, name: str = "\u6e2c\u8a66\u9ede", district: str = "\u6fb3\u9580\u534a\u5cf6") -> dict:
    return {"point_code": code, "name": name, "district": district, "lat": 22.1, "lng": 113.5, "dst": 500}


def _write_point(processed_root: Path, date: str, code: str, supermarkets: int, price_records: int) -> None:
    point_dir = processed_root / date / code
    _write_jsonl(
        point_dir / "supermarkets.jsonl",
        [{"supermarket_oid": idx, "supermarket_name": f"S{idx}"} for idx in range(supermarkets)],
    )
    rows = [
        {
            "product_oid": idx % 20,
            "product_name": f"P{idx % 20}",
            "category_id": (idx % 3) + 1,
            "supermarket_oid": idx % max(supermarkets, 1),
            "price_mop": 10 + idx,
        }
        for idx in range(price_records)
    ]
    _write_jsonl(point_dir / "category_1_prices.jsonl", rows)


def _config(tmp_path: Path, points: list[dict]) -> Path:
    path = tmp_path / "collection_points.json"
    path.write_text(json.dumps(points, ensure_ascii=False), encoding="utf-8")
    return path


def test_coverage_report_can_be_generated(tmp_path: Path) -> None:
    processed_root = tmp_path / "processed"
    config_path = _config(tmp_path, [_point("p001")])
    _write_point(processed_root, "2026-04-28", "p001", supermarkets=5, price_records=500)

    report = build_coverage_report(max_points=1, date="latest", config_path=config_path, processed_root=processed_root)

    assert report["date"] == "2026-04-28"
    assert report["summary"]["total_points"] == 1
    assert report["points"][0]["coverage_level"] == "good"


def test_good_medium_low_coverage_levels(tmp_path: Path) -> None:
    processed_root = tmp_path / "processed"
    config_path = _config(tmp_path, [_point("good"), _point("medium"), _point("low")])
    _write_point(processed_root, "2026-04-28", "good", supermarkets=5, price_records=500)
    _write_point(processed_root, "2026-04-28", "medium", supermarkets=2, price_records=100)
    _write_point(processed_root, "2026-04-28", "low", supermarkets=1, price_records=99)

    report = build_coverage_report(max_points=3, date="2026-04-28", config_path=config_path, processed_root=processed_root)

    levels = {point["point_code"]: point["coverage_level"] for point in report["points"]}
    assert levels == {"good": "good", "medium": "medium", "low": "low"}


def test_invalid_district_needs_review(tmp_path: Path) -> None:
    processed_root = tmp_path / "processed"
    config_path = _config(tmp_path, [_point("p001", district="\u672a\u77e5")])
    _write_point(processed_root, "2026-04-28", "p001", supermarkets=5, price_records=500)

    point = build_coverage_report(max_points=1, date="2026-04-28", config_path=config_path, processed_root=processed_root)["points"][0]

    assert point["needs_review"] is True
    assert "district missing / invalid" in point["warnings"]


def test_no_price_records_is_low_and_needs_review(tmp_path: Path) -> None:
    processed_root = tmp_path / "processed"
    config_path = _config(tmp_path, [_point("p001")])
    _write_point(processed_root, "2026-04-28", "p001", supermarkets=5, price_records=0)

    point = build_coverage_report(max_points=1, date="2026-04-28", config_path=config_path, processed_root=processed_root)["points"][0]

    assert point["coverage_level"] == "low"
    assert point["needs_review"] is True
    assert "no price records" in point["warnings"]


def test_summary_district_counts(tmp_path: Path) -> None:
    processed_root = tmp_path / "processed"
    config_path = _config(tmp_path, [_point("p001", district="\u6fb3\u9580\u534a\u5cf6"), _point("p002", district="\u6c39\u4ed4")])
    _write_point(processed_root, "2026-04-28", "p001", supermarkets=5, price_records=500)
    _write_point(processed_root, "2026-04-28", "p002", supermarkets=2, price_records=100)

    summary = build_coverage_report(max_points=2, date="2026-04-28", config_path=config_path, processed_root=processed_root)["summary"]

    assert summary["district_counts"] == {"\u6fb3\u9580\u534a\u5cf6": 1, "\u6c39\u4ed4": 1}


def test_markdown_contains_point_table(tmp_path: Path) -> None:
    processed_root = tmp_path / "processed"
    config_path = _config(tmp_path, [_point("p001", name="\u9ad8\u58eb\u5fb7")])
    _write_point(processed_root, "2026-04-28", "p001", supermarkets=5, price_records=500)

    markdown = render_markdown(build_coverage_report(max_points=1, date="2026-04-28", config_path=config_path, processed_root=processed_root))

    assert "## Point table" in markdown
    assert "| point_code | name | district | supermarkets | products | price_records | coverage_level | needs_review | warnings |" in markdown
    assert "| p001 | \u9ad8\u58eb\u5fb7 | \u6fb3\u9580\u534a\u5cf6 |" in markdown


def test_missing_processed_point_does_not_crash(tmp_path: Path) -> None:
    processed_root = tmp_path / "processed"
    (processed_root / "2026-04-28").mkdir(parents=True)
    config_path = _config(tmp_path, [_point("missing")])

    point = build_coverage_report(max_points=1, date="latest", config_path=config_path, processed_root=processed_root)["points"][0]

    assert point["coverage_level"] == "low"
    assert point["needs_review"] is True
    assert "processed point directory missing" in point["warnings"]
