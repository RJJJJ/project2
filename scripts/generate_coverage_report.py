from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "collection_points.json"
DEFAULT_PROCESSED_ROOT = PROJECT_ROOT / "data" / "processed"
DEFAULT_REPORT_PATH = PROJECT_ROOT / "COVERAGE_REPORT.md"
DEFAULT_JSON_REPORT_PATH = PROJECT_ROOT / "data" / "reports" / "coverage_report.json"
VALID_DISTRICTS = {"\u6fb3\u9580\u534a\u5cf6", "\u6c39\u4ed4", "\u8def\u74b0", "\u6fb3\u5927"}


def load_collection_points(config_path: Path = DEFAULT_CONFIG_PATH, max_points: int | None = None) -> list[dict[str, Any]]:
    points = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(points, list):
        raise ValueError(f"collection points must be a list: {config_path}")
    return points[:max_points] if max_points is not None else points


def resolve_report_date(processed_root: Path = DEFAULT_PROCESSED_ROOT, date: str = "latest") -> str:
    if date != "latest":
        return date
    candidates = sorted(path.name for path in processed_root.iterdir() if path.is_dir()) if processed_root.exists() else []
    if not candidates:
        raise FileNotFoundError(f"No processed date directories found under {processed_root}")
    return candidates[-1]


def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _coverage_level(supermarkets_count: int, price_records_count: int) -> str:
    if supermarkets_count >= 5 and price_records_count >= 500:
        return "good"
    if supermarkets_count >= 2 and price_records_count >= 100:
        return "medium"
    return "low"


def summarize_point(point: dict[str, Any], date: str, processed_root: Path = DEFAULT_PROCESSED_ROOT) -> dict[str, Any]:
    point_code = str(point.get("point_code", ""))
    district = point.get("district")
    point_dir = processed_root / date / point_code
    warnings: list[str] = []

    if not point_dir.exists():
        warnings.append("processed point directory missing")
        supermarkets_count = products_count = price_records_count = category_count = 0
    else:
        supermarkets = list(_read_jsonl(point_dir / "supermarkets.jsonl"))
        price_files = sorted(point_dir.glob("category_*_prices.jsonl"))
        price_rows: list[dict[str, Any]] = []
        categories: set[str] = set()
        products: set[str] = set()
        for price_file in price_files:
            rows = list(_read_jsonl(price_file))
            price_rows.extend(rows)
            for row in rows:
                if row.get("category_id") is not None:
                    categories.add(str(row.get("category_id")))
                elif row.get("category_name"):
                    categories.add(str(row.get("category_name")))
                if row.get("product_oid") is not None:
                    products.add(str(row.get("product_oid")))
                elif row.get("product_name"):
                    products.add(str(row.get("product_name")))
        supermarkets_count = len({str(row.get("supermarket_oid") or row.get("supermarket_id") or row.get("supermarket_name")) for row in supermarkets})
        products_count = len(products)
        price_records_count = len(price_rows)
        category_count = len(categories)

    if not district or district not in VALID_DISTRICTS:
        warnings.append("district missing / invalid")
    if supermarkets_count == 0:
        warnings.append("no supermarkets")
    if price_records_count == 0:
        warnings.append("no price records")

    coverage_level = _coverage_level(supermarkets_count, price_records_count)
    needs_review = coverage_level == "low" or bool(warnings)

    return {
        "point_code": point_code,
        "name": point.get("name", ""),
        "district": district or "",
        "date": date,
        "supermarkets_count": supermarkets_count,
        "products_count": products_count,
        "price_records_count": price_records_count,
        "category_count": category_count,
        "coverage_level": coverage_level,
        "warnings": warnings,
        "needs_review": needs_review,
    }


def build_coverage_report(
    *,
    max_points: int,
    date: str = "latest",
    config_path: Path = DEFAULT_CONFIG_PATH,
    processed_root: Path = DEFAULT_PROCESSED_ROOT,
) -> dict[str, Any]:
    report_date = resolve_report_date(processed_root, date)
    points = load_collection_points(config_path, max_points)
    point_reports = [summarize_point(point, report_date, processed_root) for point in points]
    levels = Counter(point["coverage_level"] for point in point_reports)
    district_counts = Counter(point["district"] for point in point_reports if point.get("district"))
    low_points = [point["point_code"] for point in point_reports if point["coverage_level"] == "low"]
    summary = {
        "total_points": len(point_reports),
        "good_count": levels.get("good", 0),
        "medium_count": levels.get("medium", 0),
        "low_count": levels.get("low", 0),
        "needs_review_count": sum(1 for point in point_reports if point["needs_review"]),
        "district_counts": dict(district_counts),
        "low_coverage_points": low_points,
    }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "date": report_date,
        "max_points": max_points,
        "summary": summary,
        "points": point_reports,
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    points = report["points"]
    lines = [
        "# Data Coverage Report",
        "",
        f"- Generated at: {report['generated_at']}",
        f"- Date: {report['date']}",
        f"- Total points: {summary['total_points']}",
        "",
        "## Summary",
        "",
        f"- Good: {summary['good_count']}",
        f"- Medium: {summary['medium_count']}",
        f"- Low: {summary['low_count']}",
        f"- Needs review: {summary['needs_review_count']}",
        f"- District counts: {json.dumps(summary['district_counts'], ensure_ascii=False)}",
        "",
        "## Point table",
        "",
        "| point_code | name | district | supermarkets | products | price_records | coverage_level | needs_review | warnings |",
        "|---|---|---|---:|---:|---:|---|---|---|",
    ]
    for point in points:
        warnings = "; ".join(point["warnings"])
        row = {**point, "warnings_text": warnings}
        lines.append(
            "| {point_code} | {name} | {district} | {supermarkets_count} | {products_count} | {price_records_count} | {coverage_level} | {needs_review} | {warnings_text} |".format(
                **row
            )
        )

    low_points = [point for point in points if point["coverage_level"] == "low"]
    review_points = [point for point in points if point["needs_review"]]
    lines.extend(["", "## Low coverage points", ""])
    lines.extend([f"- {p['point_code']} {p['name']} ({p['district']})" for p in low_points] or ["- None"])
    lines.extend(["", "## Needs review points", ""])
    lines.extend([f"- {p['point_code']} {p['name']}: {', '.join(p['warnings']) or p['coverage_level']}" for p in review_points] or ["- None"])
    lines.extend([
        "",
        "## Next actions",
        "",
        "- Review any low coverage or needs_review points before demo/testing.",
        "- If coverage looks stale, run `python scripts/update_demo_data.py --max-points 15 --preset demo_daily` and regenerate this report.",
        "- Do not expand point count or radius from this report; use it only for QA coverage visibility.",
        "",
    ])
    return "\n".join(lines)


def write_reports(report: dict[str, Any], report_path: Path, json_report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    json_report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_markdown(report), encoding="utf-8")
    json_report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Generate processed data coverage report for collection points.")
    parser.add_argument("--max-points", type=int, default=15)
    parser.add_argument("--date", default="latest")
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--json-report-path", type=Path, default=DEFAULT_JSON_REPORT_PATH)
    args = parser.parse_args(argv)

    report = build_coverage_report(max_points=args.max_points, date=args.date)
    write_reports(report, args.report_path, args.json_report_path)
    print(f"Markdown report written: {args.report_path}")
    print(f"JSON report written: {args.json_report_path}")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
