from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date as date_type, datetime, timezone
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from scripts.fetch_collection_point import load_points
from scripts.fetch_full_category_points import DEFAULT_CONFIG, run_fetch_full_category_points
from scripts.generate_full_category_coverage_report import (
    DEFAULT_PROCESSED_ROOT,
    build_full_category_coverage_report,
    write_reports as write_full_coverage_reports,
)
from scripts.import_processed_to_sqlite import run_import_processed_to_sqlite
from scripts.update_demo_data import DEFAULT_DEMO_PROCESSED_ROOT, sync_processed_to_demo_data
from services.category_presets import resolve_categories
from services.sqlite_store import DEFAULT_DB_PATH
from services.sqlite_query_service import build_sqlite_simple_basket, connect_readonly, get_latest_date, search_product_candidates_for_point

DEFAULT_REPORT_PATH = PROJECT_ROOT / "WEEKLY_REFRESH_REPORT.md"
DEFAULT_JSON_REPORT_PATH = PROJECT_ROOT / "data" / "reports" / "weekly_refresh_report.json"
DEFAULT_FULL_COVERAGE_REPORT_PATH = PROJECT_ROOT / "FULL_CATEGORY_COVERAGE_REPORT.md"
DEFAULT_FULL_COVERAGE_JSON_PATH = PROJECT_ROOT / "data" / "reports" / "full_category_coverage_report.json"
SMOKE_TEXT_ITEMS = [
    {"keyword": "\u7c73", "quantity": 1},
    {"keyword": "\u6d17\u982d\u6c34", "quantity": 2},
    {"keyword": "\u7d19\u5dfe", "quantity": 1},
]


@dataclass(frozen=True)
class WeeklyRefreshOptions:
    date: str = date_type.today().isoformat()
    max_points: int = 15
    categories: list[int] | None = None
    processed_root: Path = DEFAULT_PROCESSED_ROOT
    db_path: Path = DEFAULT_DB_PATH
    sync_demo_data: bool = False
    skip_fetch: bool = False
    skip_sqlite_import: bool = False
    skip_smoke: bool = False
    dry_run: bool = False
    report_path: Path = DEFAULT_REPORT_PATH
    json_report_path: Path = DEFAULT_JSON_REPORT_PATH
    config_path: Path = DEFAULT_CONFIG
    demo_processed_root: Path = DEFAULT_DEMO_PROCESSED_ROOT


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _step(name: str, status: str, summary: dict[str, Any] | None = None, errors: list[str] | None = None, warnings: list[str] | None = None) -> dict[str, Any]:
    return {"name": name, "status": status, "summary": summary or {}, "errors": errors or [], "warnings": warnings or []}


def _key_result(step: dict[str, Any]) -> str:
    summary = step.get("summary") or {}
    if step["name"] == "fetch_full_category_points":
        return f"points_ok={summary.get('points_ok')}/{summary.get('points_total')}"
    if step["name"] == "full_category_coverage":
        nested = summary.get("summary") if isinstance(summary.get("summary"), dict) else summary
        return f"complete={nested.get('points_complete')}/{nested.get('points_total')}"
    if step["name"] == "sqlite_import":
        return f"price_records={summary.get('price_records_upserted')} errors={len(summary.get('errors') or [])}"
    if step["name"] == "sqlite_provider_smoke":
        return f"ok={summary.get('ok')} basket_total={summary.get('basket', {}).get('estimated_total_mop')}"
    if step["name"] == "sync_demo_data":
        return str(summary.get("synced_path") or summary.get("planned"))
    return str(summary.get("planned") or summary.get("reason") or "")


def run_sqlite_provider_smoke(*, db_path: Path, date: str, point_code: str = "p001") -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []
    if not db_path.exists():
        return {"ok": False, "date": date, "errors": [f"SQLite DB not found: {db_path}"], "warnings": warnings}
    with connect_readonly(db_path) as conn:
        selected_date = get_latest_date(conn) if date == "latest" else date
        if not selected_date:
            return {"ok": False, "date": None, "errors": ["SQLite DB has no latest date"], "warnings": warnings}
        rice = search_product_candidates_for_point(conn, selected_date, point_code, "\u7c73", 1)
        tissue = search_product_candidates_for_point(conn, selected_date, point_code, "\u7d19\u5dfe", 1)
        shampoo = search_product_candidates_for_point(conn, selected_date, point_code, "\u6d17\u982d\u6c34", 1)
        basket = build_sqlite_simple_basket(conn, selected_date, point_code, SMOKE_TEXT_ITEMS)

    rice_first = rice[0] if rice else None
    tissue_first = tissue[0] if tissue else None
    shampoo_first = shampoo[0] if shampoo else None
    if not rice_first:
        errors.append("No SQLite candidate found for 米")
    elif any(term in str(rice_first.get("product_name") or "") for term in ["\u7c73\u7c89", "\u7389\u7c73"]):
        errors.append(f"Rice smoke selected suspicious product: {rice_first.get('product_name')}")
    if not tissue_first:
        errors.append("No SQLite candidate found for 紙巾")
    elif any(term in str(tissue_first.get("product_name") or "") for term in ["\u6d88\u6bd2\u6fd5\u7d19\u5dfe", "\u842c\u7528\u6d88\u6bd2"]):
        errors.append(f"Tissue smoke selected suspicious product: {tissue_first.get('product_name')}")

    matched = {item.get("keyword"): bool(item.get("matched")) for item in basket.get("items", [])}
    if not matched.get("\u7c73"):
        errors.append("Basket smoke did not match 米")
    if not matched.get("\u7d19\u5dfe"):
        errors.append("Basket smoke did not match 紙巾")
    if shampoo_first and not matched.get("\u6d17\u982d\u6c34"):
        warnings.append("洗頭水 candidates exist but basket did not match 洗頭水")
    if not shampoo_first:
        warnings.append("No SQLite candidate found for 洗頭水")

    return {
        "ok": not errors,
        "date": selected_date,
        "point_code": point_code,
        "rice_first": rice_first,
        "tissue_first": tissue_first,
        "shampoo_first": shampoo_first,
        "basket": basket,
        "warnings": warnings,
        "errors": errors,
    }


def determine_status(steps: list[dict[str, Any]], warnings: list[str]) -> str:
    if any(step["status"] == "failed" and step["name"] != "sync_demo_data" for step in steps):
        return "failed"
    if any(step["status"] == "failed" and step["name"] == "sync_demo_data" for step in steps):
        return "partial"
    if warnings or any(step.get("warnings") for step in steps):
        return "partial"
    return "success"


def build_next_actions(status: str, failed_steps: list[str], sync_demo_data: bool) -> list[str]:
    if status == "success":
        actions = ["Review WEEKLY_REFRESH_REPORT.md and full category coverage report before deployment."]
        if sync_demo_data:
            actions.append("Review demo_data/processed changes before committing demo fallback data.")
        return actions
    actions = ["Inspect failed_steps and step errors before deploying refreshed data."]
    if "fetch_full_category_points" in failed_steps:
        actions.append("Rerun fetch after checking network/API availability.")
    if "full_category_coverage" in failed_steps:
        actions.append("Inspect FULL_CATEGORY_COVERAGE_REPORT.md for incomplete points/categories.")
    if "sqlite_import" in failed_steps:
        actions.append("Fix SQLite import errors before enabling SQLite provider smoke.")
    return actions


def run_weekly_data_refresh(
    options: WeeklyRefreshOptions,
    *,
    fetch_runner: Callable[..., dict[str, Any]] = run_fetch_full_category_points,
    coverage_builder: Callable[..., dict[str, Any]] = build_full_category_coverage_report,
    coverage_writer: Callable[[dict[str, Any], Path, Path], None] = write_full_coverage_reports,
    sqlite_import_runner: Callable[..., dict[str, Any]] = run_import_processed_to_sqlite,
    smoke_runner: Callable[..., dict[str, Any]] = run_sqlite_provider_smoke,
    syncer: Callable[..., Path] = sync_processed_to_demo_data,
    write_report: bool = True,
) -> dict[str, Any]:
    categories = options.categories or resolve_categories("1-19")
    generated_at = _now_iso()
    steps: list[dict[str, Any]] = []
    warnings: list[str] = []
    failed_steps: list[str] = []
    resolved_date = date_type.today().isoformat() if options.date == "today" else options.date

    plan = {
        "date": resolved_date,
        "max_points": options.max_points,
        "categories": categories,
        "sync_demo_data": options.sync_demo_data,
        "db_path": str(options.db_path),
        "dry_run": options.dry_run,
        "generated_at": generated_at,
    }
    steps.append(_step("plan", "planned" if options.dry_run else "success", plan))

    if options.dry_run:
        for name in ["fetch_full_category_points", "full_category_coverage"]:
            steps.append(_step(name, "planned", {"dry_run": True, "planned": True}))
        if not options.skip_sqlite_import:
            steps.append(_step("sqlite_import", "planned", {"dry_run": True, "planned": True}))
        if not options.skip_smoke:
            steps.append(_step("sqlite_provider_smoke", "planned", {"dry_run": True, "planned": True}))
        if options.sync_demo_data:
            steps.append(_step("sync_demo_data", "planned", {"dry_run": True, "planned": True}))
        status = "success"
        report = {
            "generated_at": generated_at,
            "date": resolved_date,
            "max_points": options.max_points,
            "categories": categories,
            "dry_run": True,
            "sync_demo_data": options.sync_demo_data,
            "status": status,
            "steps": steps,
            "failed_steps": [],
            "warnings": [],
            "next_actions": ["Dry run only. Rerun without --dry-run to refresh data."],
        }
        return report

    if options.skip_fetch:
        steps.append(_step("fetch_full_category_points", "skipped", {"reason": "--skip-fetch"}))
    else:
        fetch_summary = fetch_runner(
            max_points=options.max_points,
            categories=categories,
            run_date=resolved_date,
            config_path=options.config_path,
            dry_run=False,
        )
        fetch_errors = [f"failed_points: {', '.join(fetch_summary.get('failed_points') or [])}"] if fetch_summary.get("failed_points") else []
        fetch_status = "failed" if fetch_errors else "success"
        steps.append(_step("fetch_full_category_points", fetch_status, fetch_summary, fetch_errors))
        if fetch_status == "failed":
            failed_steps.append("fetch_full_category_points")

    if failed_steps:
        steps.append(_step("full_category_coverage", "skipped_due_to_failure", {"blocked_by": failed_steps}))
        steps.append(_step("sqlite_import", "skipped_due_to_failure", {"blocked_by": failed_steps}))
        steps.append(_step("sqlite_provider_smoke", "skipped_due_to_failure", {"blocked_by": failed_steps}))
    else:
        coverage = coverage_builder(date=resolved_date, max_points=options.max_points, processed_root=options.processed_root, config_path=options.config_path)
        if write_report:
            coverage_writer(coverage, DEFAULT_FULL_COVERAGE_REPORT_PATH, DEFAULT_FULL_COVERAGE_JSON_PATH)
        coverage_summary = coverage.get("summary", {})
        coverage_errors = []
        if coverage_summary.get("points_complete") != options.max_points or coverage_summary.get("failed_points"):
            coverage_errors.append("full category coverage incomplete")
        coverage_status = "failed" if coverage_errors else "success"
        steps.append(_step("full_category_coverage", coverage_status, coverage, coverage_errors))
        if coverage_status == "failed":
            failed_steps.append("full_category_coverage")

        if failed_steps:
            steps.append(_step("sqlite_import", "skipped_due_to_failure", {"blocked_by": failed_steps}))
            steps.append(_step("sqlite_provider_smoke", "skipped_due_to_failure", {"blocked_by": failed_steps}))
        else:
            if options.skip_sqlite_import:
                steps.append(_step("sqlite_import", "skipped", {"reason": "--skip-sqlite-import"}))
            else:
                sqlite_summary = sqlite_import_runner(
                    date=resolved_date,
                    max_points=options.max_points,
                    processed_root=options.processed_root,
                    config_path=options.config_path,
                    db_path=options.db_path,
                )
                sqlite_errors = [str(item) for item in sqlite_summary.get("errors") or []]
                sqlite_warnings = [str(item) for item in sqlite_summary.get("warnings") or []]
                steps.append(_step("sqlite_import", "failed" if sqlite_errors else "success", sqlite_summary, sqlite_errors, sqlite_warnings))
                warnings.extend(sqlite_warnings)
                if sqlite_errors:
                    failed_steps.append("sqlite_import")

            if options.skip_smoke:
                steps.append(_step("sqlite_provider_smoke", "skipped", {"reason": "--skip-smoke"}))
            elif failed_steps:
                steps.append(_step("sqlite_provider_smoke", "skipped_due_to_failure", {"blocked_by": failed_steps}))
            else:
                smoke = smoke_runner(db_path=options.db_path, date=resolved_date, point_code="p001")
                smoke_errors = [str(item) for item in smoke.get("errors") or []]
                smoke_warnings = [str(item) for item in smoke.get("warnings") or []]
                steps.append(_step("sqlite_provider_smoke", "failed" if smoke_errors or not smoke.get("ok") else "success", smoke, smoke_errors, smoke_warnings))
                warnings.extend(smoke_warnings)
                if smoke_errors or not smoke.get("ok"):
                    failed_steps.append("sqlite_provider_smoke")

    if options.sync_demo_data:
        if failed_steps:
            steps.append(_step("sync_demo_data", "skipped_due_to_failure", {"blocked_by": failed_steps}))
        else:
            try:
                point_codes = [str(point.get("point_code")) for point in load_points(options.config_path)[: options.max_points]]
                synced_path = syncer(resolved_date, point_codes, options.processed_root, options.demo_processed_root)
                steps.append(_step("sync_demo_data", "success", {"synced_path": str(synced_path)}))
            except Exception as exc:  # noqa: BLE001 - report partial instead of hiding sync failure
                warning = f"sync_demo_data failed: {exc}"
                warnings.append(warning)
                steps.append(_step("sync_demo_data", "failed", {}, [warning]))
                failed_steps.append("sync_demo_data")

    failed_steps = [step["name"] for step in steps if step["status"] == "failed"]
    status = determine_status(steps, warnings)
    report = {
        "generated_at": generated_at,
        "date": resolved_date,
        "max_points": options.max_points,
        "categories": categories,
        "dry_run": False,
        "sync_demo_data": options.sync_demo_data,
        "status": status,
        "steps": steps,
        "failed_steps": failed_steps,
        "warnings": warnings,
        "next_actions": build_next_actions(status, failed_steps, options.sync_demo_data),
    }
    if write_report:
        write_weekly_reports(report, options.report_path, options.json_report_path)
    return report


def render_weekly_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Weekly Data Refresh Report",
        "",
        f"- Generated at: {report['generated_at']}",
        f"- Date: {report['date']}",
        f"- Max points: {report['max_points']}",
        f"- Categories: {', '.join(str(item) for item in report['categories'])}",
        f"- Status: {report['status']}",
        f"- Sync demo_data: {str(bool(report['sync_demo_data'])).lower()}",
        "",
        "## Step Summary",
        "",
        "| step | status | key result | errors |",
        "|---|---|---|---|",
    ]
    for step in report["steps"]:
        errors = "<br>".join(str(item).replace("|", "\\|") for item in step.get("errors", [])) or ""
        lines.append(f"| {step['name']} | {step['status']} | {_key_result(step).replace('|', '\\|')} | {errors} |")
    lines.extend(["", "## Failed Steps", ""])
    if report.get("failed_steps"):
        lines.extend(f"- {step}" for step in report["failed_steps"])
    else:
        lines.append("None")
    lines.extend(["", "## Warnings", ""])
    if report.get("warnings"):
        lines.extend(f"- {warning}" for warning in report["warnings"])
    else:
        lines.append("None")
    lines.extend(["", "## Next Actions", ""])
    lines.extend(f"- {action}" for action in report.get("next_actions", []))
    return "\n".join(lines) + "\n"


def write_weekly_reports(report: dict[str, Any], report_path: Path, json_report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    json_report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_weekly_markdown(report), encoding="utf-8")
    json_report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run weekly Project2 full-category data refresh workflow.")
    parser.add_argument("--date", default=date_type.today().isoformat())
    parser.add_argument("--max-points", type=int, default=15)
    parser.add_argument("--categories", default="1-19")
    parser.add_argument("--processed-root", type=Path, default=DEFAULT_PROCESSED_ROOT)
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--sync-demo-data", action="store_true")
    parser.add_argument("--skip-fetch", action="store_true")
    parser.add_argument("--skip-sqlite-import", action="store_true")
    parser.add_argument("--skip-smoke", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--json-report-path", type=Path, default=DEFAULT_JSON_REPORT_PATH)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    options = WeeklyRefreshOptions(
        date=args.date,
        max_points=args.max_points,
        categories=resolve_categories(args.categories),
        processed_root=args.processed_root,
        db_path=args.db_path,
        sync_demo_data=args.sync_demo_data,
        skip_fetch=args.skip_fetch,
        skip_sqlite_import=args.skip_sqlite_import,
        skip_smoke=args.skip_smoke,
        dry_run=args.dry_run,
        report_path=args.report_path,
        json_report_path=args.json_report_path,
        config_path=args.config,
    )
    report = run_weekly_data_refresh(options, write_report=not options.dry_run)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
