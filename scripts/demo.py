from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from scripts.ask_processed_basket import build_result
from services.basket_text_formatter import format_basket_text
from services.collection_point_resolver import resolve_point_code


def main() -> int:
    date = "2026-04-25"
    point_code = "p001"
    text = "我想買一包米、兩支洗頭水、一包紙巾"

    print("澳門採購決策 MVP Demo")
    print(f"輸入句子：{text}")
    print()

    point = resolve_point_code(point_code=point_code)
    result = build_result(date, point_code, text, PROJECT_ROOT / "data" / "processed")
    print(format_basket_text(result, text, point))

    print()
    print("這是基於 processed JSONL 的本地 MVP demo。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
