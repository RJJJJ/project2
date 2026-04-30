from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def _should_include(record: dict[str, Any]) -> bool:
    if not record.get("needs_review"):
        return False
    if str(record.get("confidence") or "") in {"low", "medium"}:
        return True
    if str(record.get("query_type") or "") in {"unknown", "ambiguous_request", "unsupported_request", "multiple_candidates"}:
        return True
    if str(record.get("status") or "") in {"ambiguous", "needs_clarification", "unsupported"}:
        return True
    return False


def build_eval_cases(review_path: str | Path) -> list[dict[str, Any]]:
    path = Path(review_path)
    if not path.exists():
        return []
    seen: set[str] = set()
    cases: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        query = str(record.get("query") or "").strip()
        if not query or query in seen or not _should_include(record):
            continue
        seen.add(query)
        cases.append(
            {
                "query": query,
                "suggested_expected": {
                    "query_type": record.get("query_type") or "unknown",
                    "status": record.get("status") or "unknown",
                    "needs_manual_label": True,
                },
                "source": "review_queue",
                "reasons": record.get("reasons") or [],
            }
        )
    return cases


def main() -> int:
    parser = argparse.ArgumentParser(description="Build draft eval cases from query review queue JSONL.")
    parser.add_argument("--review-path", default="data/logs/query_review_queue.jsonl")
    parser.add_argument("--output-path", default="data/eval/review_queue_eval_cases.json")
    args = parser.parse_args()
    cases = build_eval_cases(args.review_path)
    output = Path(args.output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"cases: {len(cases)}")
    print(f"output: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
