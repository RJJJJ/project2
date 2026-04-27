from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from scripts.ask_processed_basket import build_result
from scripts.fetch_collection_point import DEFAULT_CONFIG, fetch_point, load_points
from scripts.validate_processed_data import read_jsonl
from services.category_presets import resolve_categories
from services.consumer_price_api import ConsumerPriceApi
from services.historical_price_signal_analyzer import analyze_historical_price_signals
from services.price_signal_analyzer import analyze_point_signals
from services.watchlist_alert_service import generate_watchlist_alerts


DEFAULT_MAX_POINTS = 5
DEFAULT_PRESET = "demo_daily"
DEFAULT_PROCESSED_ROOT = PROJECT_ROOT / "data" / "processed"
DEFAULT_DEMO_PROCESSED_ROOT = PROJECT_ROOT / "demo_data" / "processed"
DEFAULT_REPORT_PATH = PROJECT_ROOT / "UPDATE_REPORT.md"
DEFAULT_JSON_REPORT_PATH = PROJECT_ROOT / "data" / "reports" / "update_report.json"
DEFAULT_TEST_TEXT = "我想買一包米、兩支洗頭水、一包紙巾"


@dataclass(frozen=True)
class UpdateOptions:
    max_points: int = DEFAULT_MAX_POINTS
    preset: str = DEFAULT_PRESET
    run_date: str = date.today().isoformat()
    sync_demo_data: bool = False
    dry_run: bool = False
    processed_root: Path = DEFAULT_PROCESSED_ROOT
    demo_processed_root: Path = DEFAULT_DEMO_PROCESSED_ROOT
    report_path: Path = DEFAULT_REPORT_PATH
    json_report_path: Path = DEFAULT_JSON_REPORT_PATH
    config_path: Path = DEFAULT_CONFIG


def _iso_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _markdown_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return "<br>".join(str(item).replace("|", "\\|") for item in value)
    return str(value).replace("|", "\\|").replace("\n", " ")


def latest_processed_date(
    processed_root: Path = DEFAULT_PROCESSED_ROOT,
    point_codes: list[str] | None = None,
) -> str | None:
    if not processed_root.exists():
        return None
    dates: list[str] = []
    for path in processed_root.iterdir():
        if not path.is_dir():
            continue
        if point_codes and not any((path / point_code).exists() for point_code in point_codes):
            continue
        dates.append(path.name)
    return sorted(dates)[-1] if dates else None


def resolve_update_date(date_arg: str, processed_root: Path, point_codes: list[str]) -> str:
    normalized = (date_arg or "today").strip().lower()
    if normalized in {"today", "manual"}:
        return date.today().isoformat()
    if normalized == "latest":
        latest = latest_processed_date(processed_root, point_codes)
        if not latest:
            raise ValueError(f"No processed date found under {processed_root}")
        return latest
    return date_arg


def validate_processed_data(date_value: str, point_code: str, processed_root: Path) -> dict[str, Any]:
    point_dir = processed_root / date_value / point_code
    result: dict[str, Any] = {
        "ok": False,
        "supermarket_rows_count": 0,
        "price_rows_count": 0,
        "warnings": [],
        "errors": [],
    }
    if not point_dir.exists():
        result["errors"].append(f"processed directory not found: {point_dir}")
        return result

    supermarket_path = point_dir / "supermarkets.jsonl"
    if not supermarket_path.exists():
        result["errors"].append("supermarkets.jsonl not found")
    else:
        supermarket_rows = read_jsonl(supermarket_path)
        result["supermarket_rows_count"] = len(supermarket_rows)
        if not supermarket_rows:
            result["warnings"].append("supermarkets.jsonl has no rows")

    price_rows_count = 0
    price_files = sorted(point_dir.glob("category_*_prices.jsonl"))
    if not price_files:
        result["errors"].append("category_*_prices.jsonl not found")
    for path in price_files:
        price_rows_count += len(read_jsonl(path))
    result["price_rows_count"] = price_rows_count
    if price_files and price_rows_count <= 0:
        result["errors"].append("price rows count is 0")

    result["ok"] = not result["errors"]
    return result


def _selected_total(result: dict[str, Any]) -> float | None:
    plans = _safe_list(result.get("plans"))
    recommended_type = result.get("recommended_plan_type")
    selected = next((plan for plan in plans if plan.get("plan_type") == recommended_type), None)
    selected = selected or next((plan for plan in plans if plan.get("estimated_total_mop") is not None), None)
    if not selected:
        return None
    total = selected.get("estimated_total_mop")
    return float(total) if total is not None else None


def run_basket_smoke(
    date_value: str,
    point_code: str,
    processed_root: Path,
    text: str = DEFAULT_TEST_TEXT,
    basket_builder: Callable[[str, str, str, Path], dict[str, Any]] = build_result,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ok": False,
        "basket_total": None,
        "recommended_plan_type": None,
        "sample_watchlist_item": None,
        "warnings": [],
        "errors": [],
    }
    try:
        basket = basket_builder(date_value, point_code, text, processed_root)
        plans = _safe_list(basket.get("plans"))
        total = _selected_total(basket)
        recommended_type = basket.get("recommended_plan_type")
        result["basket_total"] = total
        result["recommended_plan_type"] = recommended_type
        result["warnings"].extend(_safe_list(basket.get("warnings")))
        if not plans:
            result["warnings"].append("basket pipeline returned no plans")
        if recommended_type is None:
            result["warnings"].append("basket pipeline returned no recommended_plan_type")
        if total is None:
            result["warnings"].append("basket pipeline returned no estimated_total_mop")
        for plan in plans:
            for item in _safe_list(plan.get("items")):
                product_oid = item.get("product_oid")
                if product_oid is not None:
                    result["sample_watchlist_item"] = {
                        "product_oid": product_oid,
                        "product_name": item.get("product_name") or item.get("keyword"),
                    }
                    break
            if result["sample_watchlist_item"]:
                break
        result["ok"] = bool(plans and recommended_type is not None and total is not None)
    except Exception as exc:  # noqa: BLE001 - update report should collect point failures.
        result["errors"].append(f"basket pipeline failed: {exc}")
    return result


def run_signals_smoke(
    date_value: str,
    point_code: str,
    processed_root: Path,
    signals_analyzer: Callable[[str, str, Path], dict[str, Any]] = analyze_point_signals,
) -> dict[str, Any]:
    result: dict[str, Any] = {"ok": False, "largest_gap_count": 0, "errors": []}
    try:
        signals = signals_analyzer(date_value, point_code, processed_root)
        result["ok"] = True
        result["largest_gap_count"] = len(_safe_list(signals.get("largest_price_gap")))
    except Exception as exc:  # noqa: BLE001 - update report should collect point failures.
        result["errors"].append(f"price signal analyzer failed: {exc}")
    return result


def run_historical_signals_smoke(
    date_value: str,
    point_code: str,
    processed_root: Path,
    historical_signals_analyzer: Callable[..., dict[str, Any]] = analyze_historical_price_signals,
) -> dict[str, Any]:
    result: dict[str, Any] = {"ok": False, "signals_count": 0, "warnings": [], "errors": []}
    try:
        signals = historical_signals_analyzer(
            point_code=point_code,
            current_date=date_value,
            lookback_days=30,
            top_n=10,
            processed_root=processed_root,
        )
        result["ok"] = True
        result["signals_count"] = len(_safe_list(signals.get("signals")))
        result["warnings"].extend(str(item) for item in _safe_list(signals.get("warnings")))
    except Exception as exc:  # noqa: BLE001 - update report should collect point failures.
        result["errors"].append(f"historical price signal analyzer failed: {exc}")
    return result


def run_watchlist_alerts_smoke(
    date_value: str,
    point_code: str,
    processed_root: Path,
    sample_item: dict[str, Any] | None,
    watchlist_alert_generator: Callable[..., dict[str, Any]] = generate_watchlist_alerts,
) -> dict[str, Any]:
    result: dict[str, Any] = {"ok": False, "alerts_count": 0, "notify_count": 0, "warnings": [], "errors": []}
    if not sample_item or sample_item.get("product_oid") is None:
        result["ok"] = True
        result["warnings"].append("basket smoke returned no product_oid for watchlist alert smoke")
        return result
    try:
        alerts = watchlist_alert_generator(
            point_code=point_code,
            items=[sample_item],
            date=date_value,
            lookback_days=30,
            processed_root=processed_root,
        )
        summary = alerts.get("summary") or {}
        result["ok"] = True
        result["alerts_count"] = int(summary.get("alerts_count") or len(_safe_list(alerts.get("alerts"))))
        result["notify_count"] = int(summary.get("notify_count") or 0)
        result["warnings"].extend(str(item) for item in _safe_list(alerts.get("warnings")))
        for item_warning in _safe_list(alerts.get("item_warnings")):
            result["warnings"].extend(str(item) for item in _safe_list(item_warning.get("warnings")))
    except Exception as exc:  # noqa: BLE001 - update report should collect point failures.
        result["errors"].append(f"watchlist alert generator failed: {exc}")
    return result


def summarize_point_result(
    point: dict[str, Any],
    fetch_summary: dict[str, Any] | None,
    validation: dict[str, Any],
    basket: dict[str, Any],
    signals: dict[str, Any],
    historical_signals: dict[str, Any] | None = None,
    watchlist_alerts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    historical_signals = historical_signals or {}
    watchlist_alerts = watchlist_alerts or {}
    failed_requests = _safe_list((fetch_summary or {}).get("failed_requests"))
    errors = []
    warnings = []
    errors.extend(str(item) for item in validation.get("errors", []))
    errors.extend(str(item) for item in basket.get("errors", []))
    errors.extend(str(item) for item in signals.get("errors", []))
    errors.extend(str(item) for item in historical_signals.get("errors", []))
    errors.extend(str(item) for item in watchlist_alerts.get("errors", []))
    warnings.extend(str(item) for item in validation.get("warnings", []))
    warnings.extend(str(item) for item in basket.get("warnings", []))
    historical_warnings = [str(item) for item in historical_signals.get("warnings", [])]
    alert_warnings = [str(item) for item in watchlist_alerts.get("warnings", [])]
    warnings.extend(historical_warnings)
    warnings.extend(alert_warnings)

    return {
        "point_code": point.get("point_code"),
        "name": point.get("name"),
        "district": point.get("district"),
        "fetch_ok": fetch_summary is not None and not failed_requests,
        "supermarkets_found": (fetch_summary or {}).get(
            "supermarkets_found", validation.get("supermarket_rows_count", 0)
        ),
        "products_found": (fetch_summary or {}).get("products_found", 0),
        "price_records_found": (fetch_summary or {}).get(
            "price_records_found", validation.get("price_rows_count", 0)
        ),
        "failed_requests": failed_requests,
        "validation_ok": bool(validation.get("ok")),
        "basket_ok": bool(basket.get("ok")),
        "basket_total": basket.get("basket_total"),
        "signals_ok": bool(signals.get("ok")),
        "largest_gap_count": signals.get("largest_gap_count", 0),
        "historical_signals_ok": bool(historical_signals.get("ok")),
        "historical_signals_count": historical_signals.get("signals_count", 0),
        "historical_warnings": historical_warnings,
        "watchlist_alerts_ok": bool(watchlist_alerts.get("ok")),
        "watchlist_alerts_count": watchlist_alerts.get("alerts_count", 0),
        "watchlist_alerts_notify_count": watchlist_alerts.get("notify_count", 0),
        "watchlist_alert_warnings": alert_warnings,
        "warnings": warnings,
        "errors": errors,
    }


def build_update_report(
    *,
    points: list[dict[str, Any]],
    date_value: str,
    preset: str,
    max_points: int,
    sync_demo_data: bool,
    generated_at: str | None = None,
) -> dict[str, Any]:
    failed_points = [
        str(point.get("point_code"))
        for point in points
        if not point.get("fetch_ok")
        or not point.get("validation_ok")
        or not point.get("basket_ok")
        or not point.get("signals_ok")
        or point.get("historical_signals_ok") is False
        or point.get("watchlist_alerts_ok") is False
    ]
    return {
        "generated_at": generated_at or _iso_now(),
        "date": date_value,
        "preset": preset,
        "max_points": max_points,
        "sync_demo_data": sync_demo_data,
        "points": points,
        "summary": {
            "points_total": len(points),
            "points_fetch_ok": sum(1 for point in points if point.get("fetch_ok")),
            "points_basket_ok": sum(1 for point in points if point.get("basket_ok")),
            "points_signals_ok": sum(1 for point in points if point.get("signals_ok")),
            "points_historical_signals_ok": sum(1 for point in points if point.get("historical_signals_ok")),
            "points_watchlist_alerts_ok": sum(1 for point in points if point.get("watchlist_alerts_ok")),
            "failed_points": failed_points,
        },
    }


def build_markdown_report(report: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    failed_points = summary.get("failed_points") or []
    lines = [
        "# Weekly Demo Data Update Report",
        "",
        f"- Generated at: {report.get('generated_at')}",
        f"- Update date: {report.get('date')}",
        f"- Preset: {report.get('preset')}",
        f"- Max points: {report.get('max_points')}",
        f"- Sync demo_data: {str(bool(report.get('sync_demo_data'))).lower()}",
        "",
        "## Point Results",
        "",
        "| point_code | name | district | supermarkets | products | price_records | fetch_ok | validation_ok | basket_ok | signals_ok | historical_ok | historical_count | alerts_ok | alerts_count | notify_count | errors |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for point in report.get("points") or []:
        lines.append(
            "| "
            + " | ".join(
                [
                    _markdown_value(point.get("point_code")),
                    _markdown_value(point.get("name")),
                    _markdown_value(point.get("district")),
                    _markdown_value(point.get("supermarkets_found")),
                    _markdown_value(point.get("products_found")),
                    _markdown_value(point.get("price_records_found")),
                    _markdown_value(point.get("fetch_ok")),
                    _markdown_value(point.get("validation_ok")),
                    _markdown_value(point.get("basket_ok")),
                    _markdown_value(point.get("signals_ok")),
                    _markdown_value(point.get("historical_signals_ok")),
                    _markdown_value(point.get("historical_signals_count")),
                    _markdown_value(point.get("watchlist_alerts_ok")),
                    _markdown_value(point.get("watchlist_alerts_count")),
                    _markdown_value(point.get("watchlist_alerts_notify_count")),
                    _markdown_value(point.get("errors")),
                ]
            )
            + " |"
        )

    lines.extend(["", "## Failed Points", ""])
    if failed_points:
        for point_code in failed_points:
            lines.append(f"- {point_code}")
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Next Steps",
            "",
            "- If any point failed, inspect `errors` and rerun the update for the same date after fixing the cause.",
            "- For deployment fallback data, rerun with `--sync-demo-data` and commit `demo_data/processed` plus this report.",
            "- Do not commit `data/raw` or `data/processed`.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_update_reports(report: dict[str, Any], report_path: Path, json_report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(build_markdown_report(report), encoding="utf-8")
    json_report_path.parent.mkdir(parents=True, exist_ok=True)
    json_report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sync_processed_to_demo_data(
    date_value: str,
    point_codes: list[str],
    processed_root: Path = DEFAULT_PROCESSED_ROOT,
    demo_processed_root: Path = DEFAULT_DEMO_PROCESSED_ROOT,
) -> Path:
    source_date_dir = processed_root / date_value
    if processed_root.name != "processed" or processed_root.parent.name != "data":
        raise ValueError(f"Refusing to sync from unexpected processed root: {processed_root}")
    if not source_date_dir.exists():
        raise FileNotFoundError(f"Processed source date directory not found: {source_date_dir}")

    missing = [point_code for point_code in point_codes if not (source_date_dir / point_code).exists()]
    if missing:
        raise FileNotFoundError(f"Processed source point directories not found: {', '.join(missing)}")

    tmp_root = demo_processed_root.parent / "processed_tmp"
    backup_root = demo_processed_root.parent / "processed_backup"
    if tmp_root.exists():
        shutil.rmtree(tmp_root)
    if backup_root.exists():
        shutil.rmtree(backup_root)

    tmp_date_dir = tmp_root / date_value
    tmp_date_dir.mkdir(parents=True, exist_ok=True)
    for point_code in point_codes:
        shutil.copytree(source_date_dir / point_code, tmp_date_dir / point_code)

    try:
        if demo_processed_root.exists():
            demo_processed_root.replace(backup_root)
        try:
            tmp_root.replace(demo_processed_root)
        except PermissionError:
            # Windows can reject os.replace for directories even after the target
            # has been moved; shutil.move keeps the temp-root swap atomic enough
            # for local demo data while preserving the backup rollback below.
            shutil.move(str(tmp_root), str(demo_processed_root))
        if backup_root.exists():
            shutil.rmtree(backup_root)
    except Exception:
        if demo_processed_root.exists() and demo_processed_root.name == "processed":
            shutil.rmtree(demo_processed_root, ignore_errors=True)
        if backup_root.exists():
            backup_root.replace(demo_processed_root)
        raise
    return demo_processed_root / date_value


def collect_update_results(
    options: UpdateOptions,
    fetcher: Callable[[dict[str, Any], list[int], str, ConsumerPriceApi | None], dict[str, Any]] = fetch_point,
    basket_builder: Callable[[str, str, str, Path], dict[str, Any]] = build_result,
    signals_analyzer: Callable[[str, str, Path], dict[str, Any]] = analyze_point_signals,
    historical_signals_analyzer: Callable[..., dict[str, Any]] = analyze_historical_price_signals,
    watchlist_alert_generator: Callable[..., dict[str, Any]] = generate_watchlist_alerts,
) -> dict[str, Any]:
    selected_points = load_points(options.config_path)[: options.max_points]
    point_codes = [str(point["point_code"]) for point in selected_points]
    run_date = resolve_update_date(options.run_date, options.processed_root, point_codes)
    categories = resolve_categories(None, options.preset)
    client = ConsumerPriceApi()

    point_results: list[dict[str, Any]] = []
    for point in selected_points:
        point_code = str(point["point_code"])
        fetch_summary: dict[str, Any] | None = None
        if not options.dry_run:
            try:
                fetch_summary = fetcher(point, categories, run_date, client)
            except Exception as exc:  # noqa: BLE001 - collect per-point failure.
                fetch_summary = {
                    "supermarkets_found": 0,
                    "products_found": 0,
                    "price_records_found": 0,
                    "failed_requests": [{"point_code": point_code, "error": repr(exc)}],
                }

        validation = validate_processed_data(run_date, point_code, options.processed_root)
        if options.dry_run and validation.get("ok"):
            fetch_summary = {
                "supermarkets_found": validation.get("supermarket_rows_count", 0),
                "products_found": 0,
                "price_records_found": validation.get("price_rows_count", 0),
                "failed_requests": [],
            }
        basket = run_basket_smoke(run_date, point_code, options.processed_root, basket_builder=basket_builder)
        signals = run_signals_smoke(run_date, point_code, options.processed_root, signals_analyzer=signals_analyzer)
        historical_signals = run_historical_signals_smoke(
            run_date,
            point_code,
            options.processed_root,
            historical_signals_analyzer=historical_signals_analyzer,
        )
        watchlist_alerts = run_watchlist_alerts_smoke(
            run_date,
            point_code,
            options.processed_root,
            basket.get("sample_watchlist_item"),
            watchlist_alert_generator=watchlist_alert_generator,
        )
        point_results.append(
            summarize_point_result(point, fetch_summary, validation, basket, signals, historical_signals, watchlist_alerts)
        )

    return build_update_report(
        points=point_results,
        date_value=run_date,
        preset=options.preset,
        max_points=options.max_points,
        sync_demo_data=options.sync_demo_data and not options.dry_run,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch, validate, report, and optionally sync weekly demo data.")
    parser.add_argument("--max-points", type=int, default=DEFAULT_MAX_POINTS)
    parser.add_argument("--preset", default=DEFAULT_PRESET)
    parser.add_argument("--date", default="today", help="today, latest, manual, or an ISO date (YYYY-MM-DD).")
    parser.add_argument("--sync-demo-data", action="store_true")
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--json-report-path", default=str(DEFAULT_JSON_REPORT_PATH))
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    run_date_arg = "latest" if args.dry_run and args.date == "today" else args.date
    options = UpdateOptions(
        max_points=args.max_points,
        preset=args.preset,
        run_date=run_date_arg,
        sync_demo_data=args.sync_demo_data,
        dry_run=args.dry_run,
        report_path=Path(args.report_path),
        json_report_path=Path(args.json_report_path),
    )

    report = collect_update_results(options)
    point_codes = [str(point.get("point_code")) for point in report.get("points", [])]

    if options.sync_demo_data and not options.dry_run:
        sync_processed_to_demo_data(report["date"], point_codes, options.processed_root, options.demo_processed_root)

    if options.dry_run:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        write_update_reports(report, options.report_path, options.json_report_path)
        print(f"Markdown report written: {options.report_path}")
        print(f"JSON report written: {options.json_report_path}")
        print(json.dumps(report["summary"], ensure_ascii=False, indent=2))

    return 1 if report["summary"]["failed_points"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
