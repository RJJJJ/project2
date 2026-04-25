from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from scripts.ask_processed_basket import build_result
from services.collection_point_resolver import load_collection_points
from services.price_signal_analyzer import analyze_point_signals


DEFAULT_MAX_POINTS = 5
DEFAULT_PRESET = "demo_daily"
DEFAULT_TEST_TEXT = "我想買一包米、兩支洗頭水、一包紙巾"
DEFAULT_PROCESSED_ROOT = PROJECT_ROOT / "data" / "processed"
DEFAULT_REPORT_PATH = PROJECT_ROOT / "POINT_TEST_REPORT.md"


def has_processed_data(date: str, point_code: str, processed_root: Path = DEFAULT_PROCESSED_ROOT) -> bool:
    point_dir = processed_root / date / point_code
    return point_dir.exists() and any(point_dir.glob("category_*_prices.jsonl"))


def latest_processed_date_for_point(
    point_code: str,
    processed_root: Path = DEFAULT_PROCESSED_ROOT,
) -> str | None:
    if not processed_root.exists():
        return None
    dates = [
        path.name
        for path in processed_root.iterdir()
        if path.is_dir() and has_processed_data(path.name, point_code, processed_root)
    ]
    return sorted(dates)[-1] if dates else None


def _selected_total(result: dict[str, Any]) -> float | None:
    plans = result.get("plans") or []
    recommended_type = result.get("recommended_plan_type")
    selected = next((plan for plan in plans if plan.get("plan_type") == recommended_type), None)
    selected = selected or next(
        (plan for plan in plans if plan.get("estimated_total_mop") is not None),
        None,
    )
    if not selected:
        return None
    total = selected.get("estimated_total_mop")
    return float(total) if total is not None else None


def verify_point(
    point: dict[str, Any],
    text: str = DEFAULT_TEST_TEXT,
    processed_root: Path = DEFAULT_PROCESSED_ROOT,
) -> dict[str, Any]:
    point_code = str(point.get("point_code") or "")
    summary: dict[str, Any] = {
        "point_code": point_code,
        "name": point.get("name"),
        "district": point.get("district"),
        "has_processed_data": False,
        "basket_ok": False,
        "basket_total": None,
        "recommended_plan_type": None,
        "signals_ok": False,
        "largest_gap_count": 0,
        "warnings": [],
        "errors": [],
    }

    date = latest_processed_date_for_point(point_code, processed_root)
    if not date:
        summary["errors"].append("processed data not found")
        return summary

    summary["has_processed_data"] = True

    try:
        result = build_result(date, point_code, text, processed_root)
        summary["basket_ok"] = True
        summary["basket_total"] = _selected_total(result)
        summary["recommended_plan_type"] = result.get("recommended_plan_type")
        summary["warnings"].extend(result.get("warnings") or [])
    except Exception as exc:  # noqa: BLE001 - verification report should collect failures per point.
        summary["errors"].append(f"basket pipeline failed: {exc}")

    try:
        signals = analyze_point_signals(date, point_code, processed_root)
        summary["signals_ok"] = True
        summary["largest_gap_count"] = len(signals.get("largest_price_gap") or [])
    except Exception as exc:  # noqa: BLE001 - verification report should collect failures per point.
        summary["errors"].append(f"price signal analyzer failed: {exc}")

    return summary


def verify_points(
    max_points: int = DEFAULT_MAX_POINTS,
    text: str = DEFAULT_TEST_TEXT,
    processed_root: Path = DEFAULT_PROCESSED_ROOT,
) -> list[dict[str, Any]]:
    points = load_collection_points()[:max_points]
    return [verify_point(point, text=text, processed_root=processed_root) for point in points]


def _markdown_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "<br>".join(str(item).replace("|", "\\|") for item in value) or ""
    return str(value).replace("|", "\\|")


def build_markdown_report(
    summaries: list[dict[str, Any]],
    text: str = DEFAULT_TEST_TEXT,
    generated_at: datetime | None = None,
) -> str:
    generated_at = generated_at or datetime.now()
    failed_points = [
        item
        for item in summaries
        if not item["has_processed_data"] or not item["basket_ok"] or not item["signals_ok"]
    ]

    lines = [
        "# 多地區 MVP 驗收報告",
        "",
        f"- 生成時間：{generated_at.isoformat(timespec='seconds')}",
        f"- 測試句子：{text}",
        "",
        "## 每個 point 的結果",
        "",
        "| point_code | name | district | has_processed_data | basket_ok | basket_total | recommended_plan_type | signals_ok | largest_gap_count | warnings | errors |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in summaries:
        lines.append(
            "| "
            + " | ".join(
                [
                    _markdown_value(item["point_code"]),
                    _markdown_value(item["name"]),
                    _markdown_value(item["district"]),
                    _markdown_value(item["has_processed_data"]),
                    _markdown_value(item["basket_ok"]),
                    _markdown_value(item["basket_total"]),
                    _markdown_value(item["recommended_plan_type"]),
                    _markdown_value(item["signals_ok"]),
                    _markdown_value(item["largest_gap_count"]),
                    _markdown_value(item["warnings"]),
                    _markdown_value(item["errors"]),
                ]
            )
            + " |"
        )

    lines.extend(["", "## Failed Points", ""])
    if failed_points:
        for item in failed_points:
            lines.append(f"- {item['point_code']} {item.get('name') or ''}: {', '.join(item['errors'])}")
    else:
        lines.append("- 無")

    lines.extend(
        [
            "",
            "## 下一步建議",
            "",
            "- 若有 point 缺少 processed data，先執行：`python scripts/fetch_demo_points.py --max-points 5 --preset demo_daily`",
            "- 若 basket pipeline 失敗，檢查該 point 的商品價格 JSONL 是否包含測試句子的商品關鍵字。",
            "- 若 signals 失敗，檢查該 point 是否有至少一個 `category_*_prices.jsonl` 檔案且 JSONL 格式有效。",
        ]
    )
    return "\n".join(lines) + "\n"


def write_markdown_report(
    summaries: list[dict[str, Any]],
    report_path: Path = DEFAULT_REPORT_PATH,
    text: str = DEFAULT_TEST_TEXT,
) -> Path:
    report_path.write_text(build_markdown_report(summaries, text=text), encoding="utf-8")
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify MVP basket and signal support for demo collection points.")
    parser.add_argument("--max-points", type=int, default=DEFAULT_MAX_POINTS)
    parser.add_argument("--preset", default=DEFAULT_PRESET)
    parser.add_argument("--processed-root", default=str(DEFAULT_PROCESSED_ROOT))
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    processed_root = Path(args.processed_root)
    summaries = verify_points(max_points=args.max_points, processed_root=processed_root)
    missing = [item for item in summaries if not item["has_processed_data"]]
    if missing:
        print(
            "部分 collection points 尚未有 processed data。請先跑：\n"
            f"python scripts/fetch_demo_points.py --max-points {args.max_points} --preset {args.preset}"
        )

    print(json.dumps({"points": summaries}, ensure_ascii=False, indent=2))

    if args.write_report:
        report_path = write_markdown_report(summaries)
        print(f"Markdown report written: {report_path}")

    failed = [
        item
        for item in summaries
        if not item["has_processed_data"] or not item["basket_ok"] or not item["signals_ok"]
    ]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
