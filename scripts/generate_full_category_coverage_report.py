from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.fetch_collection_point import load_points
from scripts.verify_full_category_point import EXPECTED_FILES, count_jsonl_rows, resolve_latest_date

DEFAULT_CONFIG = PROJECT_ROOT / "config" / "collection_points.json"
DEFAULT_PROCESSED_ROOT = PROJECT_ROOT / "data" / "processed"
DEFAULT_REPORT_PATH = PROJECT_ROOT / "FULL_CATEGORY_COVERAGE_REPORT.md"
DEFAULT_JSON_REPORT_PATH = PROJECT_ROOT / "data" / "reports" / "full_category_coverage_report.json"


def inspect_point_coverage(point: dict[str, Any], *, date: str, processed_root: Path) -> dict[str, Any]:
    point_code = str(point.get("point_code", ""))
    point_dir = processed_root / date / point_code
    files: list[dict[str, Any]] = []
    missing_files: list[str] = []
    zero_row_files: list[str] = []
    existing_target_count = 0

    for name in EXPECTED_FILES:
        path = point_dir / name
        exists = path.exists()
        rows = count_jsonl_rows(path) if exists else 0
        if exists:
            existing_target_count += 1
        else:
            missing_files.append(name)
        if exists and rows == 0:
            zero_row_files.append(name)
        files.append({"name": name, "exists": exists, "rows": rows})

    if existing_target_count == len(EXPECTED_FILES):
        coverage_level = "complete"
    elif point_dir.exists() and existing_target_count > 0:
        coverage_level = "partial"
    else:
        coverage_level = "missing"

    return {
        "point_code": point_code,
        "name": point.get("name", ""),
        "district": point.get("district", ""),
        "coverage_level": coverage_level,
        "missing_files": missing_files,
        "zero_row_files": zero_row_files,
        "files": files,
    }


def build_full_category_coverage_report(
    *,
    date: str = "latest",
    max_points: int = 15,
    processed_root: Path = DEFAULT_PROCESSED_ROOT,
    config_path: Path = DEFAULT_CONFIG,
) -> dict[str, Any]:
    resolved_date = resolve_latest_date(processed_root) if date == "latest" else date
    points = load_points(config_path)[:max_points]
    point_reports = [inspect_point_coverage(point, date=resolved_date, processed_root=processed_root) for point in points]
    failed_points = [point["point_code"] for point in point_reports if point["coverage_level"] != "complete"]
    summary = {
        "date": resolved_date,
        "points_total": len(point_reports),
        "points_complete": sum(1 for point in point_reports if point["coverage_level"] == "complete"),
        "points_partial": sum(1 for point in point_reports if point["coverage_level"] == "partial"),
        "points_missing": sum(1 for point in point_reports if point["coverage_level"] == "missing"),
        "failed_points": failed_points,
    }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "date": resolved_date,
        "max_points": max_points,
        "summary": summary,
        "points": point_reports,
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Full Category Coverage Report",
        "",
        f"- Generated at: {report['generated_at']}",
        f"- Date: {report['date']}",
        f"- Max points: {report['max_points']}",
        "",
        "## Summary",
        "",
        f"- Points total: {summary['points_total']}",
        f"- Complete: {summary['points_complete']}",
        f"- Partial: {summary['points_partial']}",
        f"- Missing: {summary['points_missing']}",
        f"- Failed points: {', '.join(summary['failed_points']) if summary['failed_points'] else 'None'}",
        "",
        "## Point table",
        "",
        "| point_code | name | district | coverage_level | missing_files | zero_row_files |",
        "|---|---|---|---|---|---|",
    ]
    for point in report["points"]:
        lines.append(
            "| {point_code} | {name} | {district} | {coverage_level} | {missing_files} | {zero_row_files} |".format(
                point_code=point["point_code"],
                name=point["name"],
                district=point["district"],
                coverage_level=point["coverage_level"],
                missing_files=", ".join(point["missing_files"]),
                zero_row_files=", ".join(point["zero_row_files"]),
            )
        )
    lines.append("")
    return "\n".join(lines)


def write_reports(report: dict[str, Any], report_path: Path, json_report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    json_report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_markdown(report), encoding="utf-8")
    json_report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Generate full category coverage report for processed data.")
    parser.add_argument("--date", default="latest")
    parser.add_argument("--max-points", type=int, default=15)
    parser.add_argument("--processed-root", type=Path, default=DEFAULT_PROCESSED_ROOT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--json-report-path", type=Path, default=DEFAULT_JSON_REPORT_PATH)
    parser.add_argument("--no-write-report", action="store_true")
    args = parser.parse_args(argv)

    report = build_full_category_coverage_report(
        date=args.date,
        max_points=args.max_points,
        processed_root=args.processed_root,
        config_path=args.config,
    )
    if not args.no_write_report:
        write_reports(report, args.report_path, args.json_report_path)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
