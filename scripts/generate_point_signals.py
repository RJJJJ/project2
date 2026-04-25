from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from services.price_signal_analyzer import analyze_point_signals


def _money(value: float | int | None) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):.1f} MOP"


def format_signals_text(signals: dict, top_n: int = 5) -> str:
    lines = [
        "本區抵買訊號",
        "",
        f"資料日期：{signals.get('date')}",
        f"採集點：{signals.get('point_code')}",
        "",
        "本區價差最大商品：",
    ]

    gaps = (signals.get("largest_price_gap") or [])[:top_n]
    if gaps:
        for item in gaps:
            lines.extend(
                [
                    f"- {item.get('product_name')} ({item.get('quantity')})",
                    f"  最低價：{_money(item.get('min_price_mop'))}",
                    f"  最高價：{_money(item.get('max_price_mop'))}",
                    f"  價差百分比：{float(item.get('gap_percent', 0.0)):.1f}%",
                    f"  最低價超市：{item.get('min_supermarket_name')}",
                    f"  最高價超市：{item.get('max_supermarket_name')}",
                ]
            )
    else:
        lines.append("- N/A")

    lines.extend(["", "價格只供參考，以店內標示為準。"])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate local price signals from processed JSONL.")
    parser.add_argument("--date", required=True)
    parser.add_argument("--point-code", required=True)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--processed-root", default=str(PROJECT_ROOT / "data" / "processed"))
    args = parser.parse_args()

    signals = analyze_point_signals(args.date, args.point_code, Path(args.processed_root))
    if args.format == "json":
        print(json.dumps(signals, ensure_ascii=False, indent=2))
    else:
        print(format_signals_text(signals))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
