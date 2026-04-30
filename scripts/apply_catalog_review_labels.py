from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def _load_json(path: str | Path) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def load_review_csv(path: str | Path) -> list[dict[str, str]]:
    review_path = Path(path)
    if not review_path.exists():
        return []
    with review_path.open("r", encoding="utf-8-sig", newline="") as fh:
        return [{str(key): str(value or "") for key, value in row.items()} for row in csv.DictReader(fh)]


def apply_review_labels_to_cases(cases: list[dict[str, Any]], review_rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    review_by_case_id = {row.get("case_id", "").strip(): row for row in review_rows if row.get("case_id", "").strip()}
    counters = {
        "input_cases": len(cases),
        "review_rows": len(review_rows),
        "promoted_to_strict": 0,
        "kept_pending": 0,
        "ignored": 0,
        "needs_revision": 0,
        "needs_data_check": 0,
        "unchanged": 0,
    }
    reviewed_cases: list[dict[str, Any]] = []
    for case in cases:
        updated = dict(case)
        review_row = review_by_case_id.get(str(case.get("case_id") or ""))
        decision = (review_row or {}).get("review_decision", "").strip()
        review_payload = {
            "decision": decision,
            "review_notes": (review_row or {}).get("review_notes", "").strip(),
            "reviewer": (review_row or {}).get("reviewer", "").strip(),
            "reviewed_at": (review_row or {}).get("reviewed_at", "").strip(),
        }
        if decision == "promote_to_strict":
            updated["needs_manual_label"] = False
            updated["enforce"] = True
            updated["status"] = "active"
            updated["review"] = review_payload
            counters["promoted_to_strict"] += 1
        elif decision == "keep_pending":
            updated["needs_manual_label"] = True
            updated["enforce"] = False
            updated["status"] = "pending"
            updated["review"] = review_payload
            counters["kept_pending"] += 1
        elif decision == "ignore_case":
            updated["needs_manual_label"] = True
            updated["enforce"] = False
            updated["status"] = "ignored"
            updated["review"] = review_payload
            counters["ignored"] += 1
        elif decision == "revise_expected":
            updated["needs_manual_label"] = True
            updated["enforce"] = False
            updated["status"] = "needs_revision"
            updated["review"] = review_payload
            counters["needs_revision"] += 1
        elif decision == "needs_data_check":
            updated["needs_manual_label"] = True
            updated["enforce"] = False
            updated["status"] = "needs_data_check"
            updated["review"] = review_payload
            counters["needs_data_check"] += 1
        else:
            counters["unchanged"] += 1
        reviewed_cases.append(updated)
    return reviewed_cases, counters


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply catalog manual review labels to adversarial cases.")
    parser.add_argument("--adversarial-cases-path", required=True)
    parser.add_argument("--review-csv", required=True)
    parser.add_argument("--output-path", required=True)
    args = parser.parse_args()

    cases = _load_json(args.adversarial_cases_path)
    review_rows = load_review_csv(args.review_csv)
    reviewed_cases, counters = apply_review_labels_to_cases(cases, review_rows)

    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(reviewed_cases, ensure_ascii=False, indent=2), encoding="utf-8")

    print("CATALOG REVIEW LABELS APPLIED")
    print(f"input_cases: {counters['input_cases']}")
    print(f"review_rows: {counters['review_rows']}")
    print(f"promoted_to_strict: {counters['promoted_to_strict']}")
    print(f"kept_pending: {counters['kept_pending']}")
    print(f"ignored: {counters['ignored']}")
    print(f"needs_revision: {counters['needs_revision']}")
    print(f"needs_data_check: {counters['needs_data_check']}")
    print(f"unchanged: {counters['unchanged']}")
    print(f"output: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
