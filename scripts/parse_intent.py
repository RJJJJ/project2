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

from services.gemini_intent_parser import DEFAULT_MODEL, parse_intent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parse shopping intent into grounded JSON intent.")
    parser.add_argument("--text", required=True)
    parser.add_argument("--no-gemini", action="store_true")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args(argv)
    payload = parse_intent(args.text, use_gemini=not args.no_gemini, model_name=args.model)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
