from __future__ import annotations

import argparse
import json
import sys
from datetime import date as date_type
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.category_presets import resolve_categories
from services.consumer_price_api import ConsumerPriceApi
from scripts.fetch_collection_point import fetch_point, load_points

DEFAULT_CONFIG = PROJECT_ROOT / "config" / "collection_points.json"

Fetcher = Callable[[dict[str, Any], list[int], str, ConsumerPriceApi | None], dict[str, Any]]


def _point_dry_run_summary(point: dict[str, Any], categories: list[int]) -> dict[str, Any]:
    return {
        "point_code": point.get("point_code"),
        "name": point.get("name", ""),
        "district": point.get("district", ""),
        "ok": True,
        "categories_processed": 0,
        "categories_planned": len(categories),
        "supermarkets_found": 0,
        "products_found": 0,
        "price_records_found": 0,
        "failed_requests": [],
    }


def run_fetch_full_category_points(
    *,
    max_points: int = 15,
    categories: list[int] | None = None,
    run_date: str | None = None,
    config_path: Path = DEFAULT_CONFIG,
    dry_run: bool = False,
    fetcher: Fetcher = fetch_point,
    client: ConsumerPriceApi | None = None,
) -> dict[str, Any]:
    resolved_date = run_date or date_type.today().isoformat()
    resolved_categories = categories or resolve_categories("1-19")
    points = load_points(config_path)[:max_points]
    point_summaries: list[dict[str, Any]] = []
    failed_points: list[str] = []

    if dry_run:
        point_summaries = [_point_dry_run_summary(point, resolved_categories) for point in points]
        return {
            "date": resolved_date,
            "max_points": max_points,
            "categories": resolved_categories,
            "dry_run": True,
            "points_total": len(points),
            "points_ok": len(points),
            "failed_points": [],
            "points": point_summaries,
        }

    shared_client = client or ConsumerPriceApi()
    for point in points:
        point_code = str(point.get("point_code", ""))
        try:
            result = fetcher(point, resolved_categories, resolved_date, shared_client)
            failed_requests = result.get("failed_requests") or []
            ok = not failed_requests
            if not ok:
                failed_points.append(point_code)
            point_summaries.append(
                {
                    "point_code": point_code,
                    "name": point.get("name", ""),
                    "district": point.get("district", ""),
                    "ok": ok,
                    "categories_processed": int(result.get("categories_processed", 0)),
                    "supermarkets_found": int(result.get("supermarkets_found", 0)),
                    "products_found": int(result.get("products_found", 0)),
                    "price_records_found": int(result.get("price_records_found", 0)),
                    "failed_requests": failed_requests,
                }
            )
        except Exception as exc:  # noqa: BLE001 - batch should continue next point
            failed_points.append(point_code)
            point_summaries.append(
                {
                    "point_code": point_code,
                    "name": point.get("name", ""),
                    "district": point.get("district", ""),
                    "ok": False,
                    "categories_processed": 0,
                    "supermarkets_found": 0,
                    "products_found": 0,
                    "price_records_found": 0,
                    "failed_requests": [{"point_code": point_code, "error": repr(exc)}],
                }
            )

    return {
        "date": resolved_date,
        "max_points": max_points,
        "categories": resolved_categories,
        "dry_run": False,
        "points_total": len(points),
        "points_ok": sum(1 for point in point_summaries if point["ok"]),
        "failed_points": failed_points,
        "points": point_summaries,
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Fetch full category data for the first N collection points.")
    parser.add_argument("--max-points", type=int, default=15)
    parser.add_argument("--categories", default="1-19")
    parser.add_argument("--date", default=date_type.today().isoformat())
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    summary = run_fetch_full_category_points(
        max_points=args.max_points,
        categories=resolve_categories(args.categories),
        run_date=args.date,
        config_path=args.config,
        dry_run=args.dry_run,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if summary["failed_points"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
