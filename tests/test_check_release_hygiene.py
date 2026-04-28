from __future__ import annotations

import json
from pathlib import Path

from scripts.check_release_hygiene import run_release_hygiene


def write_point(root: Path, point: str, categories: tuple[int, ...] = (1,)) -> None:
    point_dir = root / "demo_data" / "processed" / "2026-04-28" / point
    point_dir.mkdir(parents=True)
    (point_dir / "supermarkets.jsonl").write_text('{"name":"demo"}\n', encoding="utf-8")
    for category in categories:
        (point_dir / f"category_{category}_prices.jsonl").write_text('{"price":1}\n', encoding="utf-8")


def write_required_reports(root: Path, *, omit: str | None = None) -> None:
    reports = [
        "UPDATE_REPORT.md",
        "COVERAGE_REPORT.md",
        "FULL_CATEGORY_COVERAGE_REPORT.md",
        "WEEKLY_REFRESH_REPORT.md",
        "data/reports/update_report.json",
        "data/reports/coverage_report.json",
        "data/reports/full_category_coverage_report.json",
        "data/reports/weekly_refresh_report.json",
    ]
    for rel in reports:
        if rel == omit:
            continue
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}" if rel.endswith(".json") else "report", encoding="utf-8")


def write_config(root: Path, count: int = 15) -> None:
    config_dir = root / "config"
    config_dir.mkdir()
    points = [{"point_code": f"p{i:03d}", "name": f"P{i}"} for i in range(1, count + 1)]
    (config_dir / "collection_points.json").write_text(json.dumps(points), encoding="utf-8")


def test_demo_data_missing_is_not_ok(tmp_path: Path):
    write_config(tmp_path)
    write_required_reports(tmp_path)

    summary = run_release_hygiene(tmp_path, git_ls_files=lambda root: [])

    assert summary["ok"] is False
    assert any(check["name"] == "demo_data_exists" and not check["ok"] for check in summary["checks"])


def test_tracked_forbidden_file_is_not_ok(tmp_path: Path):
    write_config(tmp_path)
    for i in range(1, 16):
        write_point(tmp_path, f"p{i:03d}")
    write_required_reports(tmp_path)

    summary = run_release_hygiene(
        tmp_path,
        git_ls_files=lambda root: ["data/raw/example.json", "data/app_state/project2_dev.sqlite3"],
    )

    assert summary["ok"] is False
    assert "data/raw/example.json" in "\n".join(summary["errors"])
    assert "data/app_state/project2_dev.sqlite3" in "\n".join(summary["errors"])


def test_all_required_files_present_is_ok(tmp_path: Path):
    write_config(tmp_path)
    for i in range(1, 16):
        write_point(tmp_path, f"p{i:03d}")
    write_required_reports(tmp_path)

    summary = run_release_hygiene(tmp_path, git_ls_files=lambda root: ["README.md"])

    assert summary["ok"] is True
    assert summary["errors"] == []


def test_missing_optional_report_is_warning_only(tmp_path: Path):
    write_config(tmp_path)
    for i in range(1, 16):
        write_point(tmp_path, f"p{i:03d}")
    write_required_reports(tmp_path, omit="WEEKLY_REFRESH_REPORT.md")

    summary = run_release_hygiene(tmp_path, git_ls_files=lambda root: [])

    assert summary["ok"] is True
    assert "Optional report missing: WEEKLY_REFRESH_REPORT.md" in summary["warnings"]
