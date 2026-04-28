from __future__ import annotations

import json
from pathlib import Path

from scripts.generate_full_category_coverage_report import build_full_category_coverage_report, main, render_markdown
from scripts.verify_full_category_point import EXPECTED_FILES


def _write(path: Path, rows: int = 1) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join('{"ok": true}' for _ in range(rows)) + "\n", encoding="utf-8")


def _config(tmp_path: Path) -> Path:
    points = [
        {"point_code": "complete", "name": "Complete", "district": "????", "lat": 1, "lng": 2, "dst": 500},
        {"point_code": "partial", "name": "Partial", "district": "??", "lat": 1, "lng": 2, "dst": 500},
        {"point_code": "missing", "name": "Missing", "district": "??", "lat": 1, "lng": 2, "dst": 500},
    ]
    path = tmp_path / "collection_points.json"
    path.write_text(json.dumps(points, ensure_ascii=False), encoding="utf-8")
    return path


def test_complete_partial_missing_points(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    for name in EXPECTED_FILES:
        _write(processed / "2026-04-28" / "complete" / name)
    _write(processed / "2026-04-28" / "partial" / "category_1_prices.jsonl")

    report = build_full_category_coverage_report(date="latest", max_points=3, processed_root=processed, config_path=_config(tmp_path))
    levels = {point["point_code"]: point["coverage_level"] for point in report["points"]}

    assert levels == {"complete": "complete", "partial": "partial", "missing": "missing"}
    assert report["summary"]["points_complete"] == 1
    assert report["summary"]["points_partial"] == 1
    assert report["summary"]["points_missing"] == 1
    assert report["summary"]["failed_points"] == ["partial", "missing"]


def test_markdown_contains_table_header(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    for name in EXPECTED_FILES:
        _write(processed / "2026-04-28" / "complete" / name)
    report = build_full_category_coverage_report(date="2026-04-28", max_points=1, processed_root=processed, config_path=_config(tmp_path))

    markdown = render_markdown(report)

    assert "# Full Category Coverage Report" in markdown
    assert "| point_code | name | district | coverage_level | missing_files | zero_row_files |" in markdown


def test_no_write_report_does_not_write_files(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    for name in EXPECTED_FILES:
        _write(processed / "2026-04-28" / "complete" / name)
    report_path = tmp_path / "report.md"
    json_path = tmp_path / "report.json"

    exit_code = main([
        "--date", "2026-04-28",
        "--max-points", "1",
        "--processed-root", str(processed),
        "--config", str(_config(tmp_path)),
        "--report-path", str(report_path),
        "--json-report-path", str(json_path),
        "--no-write-report",
    ])

    assert exit_code == 0
    assert not report_path.exists()
    assert not json_path.exists()
