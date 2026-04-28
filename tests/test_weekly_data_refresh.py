from __future__ import annotations

from pathlib import Path

from scripts.weekly_data_refresh import WeeklyRefreshOptions, render_weekly_markdown, run_weekly_data_refresh


def _options(tmp_path: Path, **kwargs) -> WeeklyRefreshOptions:
    return WeeklyRefreshOptions(
        date="2026-04-28",
        max_points=2,
        categories=[1, 19],
        processed_root=tmp_path / "data" / "processed",
        db_path=tmp_path / "data" / "app_state" / "test.sqlite3",
        report_path=tmp_path / "WEEKLY_REFRESH_REPORT.md",
        json_report_path=tmp_path / "weekly_refresh_report.json",
        config_path=tmp_path / "collection_points.json",
        **kwargs,
    )


def _fetch_success(**kwargs):  # noqa: ANN003
    return {"date": kwargs.get("run_date"), "points_total": 2, "points_ok": 2, "failed_points": []}


def _coverage_success(**kwargs):  # noqa: ANN003
    return {"date": kwargs.get("date"), "max_points": 2, "summary": {"points_total": 2, "points_complete": 2, "failed_points": []}, "points": []}


def _import_success(**kwargs):  # noqa: ANN003
    return {"date": kwargs.get("date"), "price_records_upserted": 10, "warnings": [], "errors": []}


def _smoke_success(**kwargs):  # noqa: ANN003
    return {"ok": True, "basket": {"estimated_total_mop": 123.0}, "warnings": [], "errors": []}


def test_dry_run_does_not_call_fetcher_or_write(tmp_path: Path) -> None:
    called = {"fetch": False}

    def fetcher(**kwargs):  # noqa: ANN003
        called["fetch"] = True
        return {}

    report = run_weekly_data_refresh(_options(tmp_path, dry_run=True), fetch_runner=fetcher, write_report=False)

    assert report["dry_run"] is True
    assert report["status"] == "success"
    assert called["fetch"] is False
    assert not (tmp_path / "weekly_refresh_report.json").exists()
    assert any(step["summary"].get("dry_run") for step in report["steps"] if step["name"] == "fetch_full_category_points")


def test_all_success(tmp_path: Path) -> None:
    report = run_weekly_data_refresh(
        _options(tmp_path),
        fetch_runner=_fetch_success,
        coverage_builder=_coverage_success,
        coverage_writer=lambda *args, **kwargs: None,
        sqlite_import_runner=_import_success,
        smoke_runner=_smoke_success,
        write_report=False,
    )

    assert report["status"] == "success"
    assert report["failed_steps"] == []


def test_fetch_failed_stops_downstream(tmp_path: Path) -> None:
    def fetch_failed(**kwargs):  # noqa: ANN003
        return {"points_total": 2, "points_ok": 1, "failed_points": ["p002"]}

    report = run_weekly_data_refresh(_options(tmp_path), fetch_runner=fetch_failed, write_report=False)

    assert report["status"] == "failed"
    assert "fetch_full_category_points" in report["failed_steps"]
    assert any(step["status"] == "skipped_due_to_failure" for step in report["steps"] if step["name"] == "sqlite_import")


def test_coverage_incomplete_failed(tmp_path: Path) -> None:
    def coverage_bad(**kwargs):  # noqa: ANN003
        return {"summary": {"points_total": 2, "points_complete": 1, "failed_points": ["p002"]}}

    report = run_weekly_data_refresh(
        _options(tmp_path),
        fetch_runner=_fetch_success,
        coverage_builder=coverage_bad,
        coverage_writer=lambda *args, **kwargs: None,
        write_report=False,
    )

    assert report["status"] == "failed"
    assert "full_category_coverage" in report["failed_steps"]


def test_sqlite_import_errors_failed(tmp_path: Path) -> None:
    def import_bad(**kwargs):  # noqa: ANN003
        return {"errors": ["bad row"], "warnings": []}

    report = run_weekly_data_refresh(
        _options(tmp_path),
        fetch_runner=_fetch_success,
        coverage_builder=_coverage_success,
        coverage_writer=lambda *args, **kwargs: None,
        sqlite_import_runner=import_bad,
        write_report=False,
    )

    assert report["status"] == "failed"
    assert "sqlite_import" in report["failed_steps"]


def test_smoke_warning_partial(tmp_path: Path) -> None:
    def smoke_warning(**kwargs):  # noqa: ANN003
        return {"ok": True, "basket": {"estimated_total_mop": 123.0}, "warnings": ["no shampoo"], "errors": []}

    report = run_weekly_data_refresh(
        _options(tmp_path),
        fetch_runner=_fetch_success,
        coverage_builder=_coverage_success,
        coverage_writer=lambda *args, **kwargs: None,
        sqlite_import_runner=_import_success,
        smoke_runner=smoke_warning,
        write_report=False,
    )

    assert report["status"] == "partial"
    assert "no shampoo" in report["warnings"]


def test_report_markdown_contains_step_summary() -> None:
    markdown = render_weekly_markdown(
        {
            "generated_at": "now",
            "date": "2026-04-28",
            "max_points": 2,
            "categories": [1, 19],
            "status": "success",
            "sync_demo_data": False,
            "steps": [{"name": "plan", "status": "success", "summary": {}, "errors": [], "warnings": []}],
            "failed_steps": [],
            "warnings": [],
            "next_actions": ["done"],
        }
    )

    assert "## Step Summary" in markdown
    assert "| step | status | key result | errors |" in markdown
