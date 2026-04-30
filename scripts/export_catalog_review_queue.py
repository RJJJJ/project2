from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CSV_COLUMNS = [
    "case_id",
    "query",
    "source",
    "risk_term",
    "related_product_names",
    "expected_status",
    "expected_query_type",
    "must_include_product_names",
    "must_not_include_product_names",
    "suggested_guardrail",
    "current_needs_manual_label",
    "suggested_review_decision",
    "review_decision",
    "review_notes",
    "reviewer",
    "reviewed_at",
]

REVIEW_DECISION_MEANINGS = {
    "promote_to_strict": "Promote this case into strict enforced regression coverage.",
    "keep_pending": "Keep this case pending manual labeling for later review.",
    "ignore_case": "Ignore this case in regression because it is not useful or not valid.",
    "revise_expected": "The case is useful but expected JSON needs manual revision before promotion.",
    "needs_data_check": "Catalog data or product labeling needs validation before this case can be decided.",
}


def _load_json(path: str | Path) -> dict | list:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _join(values: list[str] | None) -> str:
    return " | ".join(str(value) for value in (values or []) if str(value).strip())


def _is_strict_case(case: dict[str, Any]) -> bool:
    if case.get("status") == "ignored":
        return False
    if case.get("enforce") is True:
        return True
    return not bool(case.get("needs_manual_label"))


def _needs_review_export(case: dict[str, Any]) -> bool:
    expected = case.get("expected") or {}
    if bool(case.get("needs_manual_label")):
        return True
    if case.get("source") == "catalog_confusion_audit" and not _is_strict_case(case):
        return True
    if not isinstance(expected, dict) or not expected:
        return True
    status_keys = {"status", "status_in", "not_status"}
    query_type_keys = {"query_type", "query_type_in"}
    if not any(key in expected for key in status_keys | query_type_keys):
        return True
    return False


def _suggested_review_decision(case: dict[str, Any]) -> str:
    expected = case.get("expected") or {}
    if not expected:
        return "revise_expected"
    if case.get("case_type") == "generic_term_guardrail" and expected.get("must_not_include_product_names"):
        return "promote_to_strict"
    if case.get("case_type") == "exact_product_guardrail":
        return "revise_expected"
    return "keep_pending"


def build_catalog_review_queue_rows(adversarial_cases: list[dict], audit_result: dict | None = None) -> list[dict[str, str]]:
    del audit_result  # reserved for future enrichment
    rows: list[dict[str, str]] = []
    for case in adversarial_cases:
        if not _needs_review_export(case):
            continue
        expected = case.get("expected") or {}
        rows.append(
            {
                "case_id": str(case.get("case_id") or ""),
                "query": str(case.get("query") or ""),
                "source": str(case.get("source") or ""),
                "risk_term": str(case.get("term") or ""),
                "related_product_names": _join(
                    list(dict.fromkeys((expected.get("must_include_product_names") or []) + (expected.get("must_not_include_product_names") or [])))
                ),
                "expected_status": str(expected.get("status") or _join(expected.get("status_in"))),
                "expected_query_type": str(expected.get("query_type") or _join(expected.get("query_type_in"))),
                "must_include_product_names": _join(expected.get("must_include_product_names") or []),
                "must_not_include_product_names": _join(expected.get("must_not_include_product_names") or []),
                "suggested_guardrail": str(case.get("case_type") or ""),
                "current_needs_manual_label": "true" if bool(case.get("needs_manual_label")) else "false",
                "suggested_review_decision": _suggested_review_decision(case),
                "review_decision": "",
                "review_notes": "",
                "reviewer": "",
                "reviewed_at": "",
            }
        )
    return rows


def write_review_queue_csv(rows: list[dict[str, str]], output_csv: str | Path) -> Path:
    path = Path(output_csv)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in CSV_COLUMNS})
    return path


def write_review_queue_markdown(rows: list[dict[str, str]], output_md: str | Path) -> Path:
    path = Path(output_md)
    path.parent.mkdir(parents=True, exist_ok=True)
    by_risk_term = Counter(row["risk_term"] or "(blank)" for row in rows)
    by_guardrail = Counter(row["suggested_guardrail"] or "(blank)" for row in rows)
    by_decision = Counter(row["suggested_review_decision"] or "(blank)" for row in rows)
    lines = [
        "# Catalog Adversarial Manual Review Queue",
        "",
        "## Summary",
        f"- total pending cases: {len(rows)}",
        "- by risk_term:",
    ]
    lines.extend([f"  - {key}: {value}" for key, value in sorted(by_risk_term.items())] or ["  - none"])
    lines.append("- by suggested_guardrail:")
    lines.extend([f"  - {key}: {value}" for key, value in sorted(by_guardrail.items())] or ["  - none"])
    lines.append("- by suggested_review_decision:")
    lines.extend([f"  - {key}: {value}" for key, value in sorted(by_decision.items())] or ["  - none"])
    lines.extend(["", "## Review Instructions"])
    for decision, meaning in REVIEW_DECISION_MEANINGS.items():
        lines.append(f"- `{decision}`: {meaning}")
    lines.extend(
        [
            "",
            "## Pending Cases Table",
            "",
            "| case_id | query | risk_term | related_product_names | suggested_guardrail | suggested_review_decision | review_decision |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        lines.append(
            "| {case_id} | {query} | {risk_term} | {related_product_names} | {suggested_guardrail} | {suggested_review_decision} | {review_decision} |".format(
                **{key: str(value).replace("|", "/") for key, value in row.items()}
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Export catalog adversarial manual review queue to CSV and Markdown.")
    parser.add_argument("--adversarial-cases-path", required=True)
    parser.add_argument("--audit-path", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--output-md", required=True)
    args = parser.parse_args()

    adversarial_cases = _load_json(args.adversarial_cases_path)
    audit_result = _load_json(args.audit_path)
    rows = build_catalog_review_queue_rows(adversarial_cases if isinstance(adversarial_cases, list) else [], audit_result if isinstance(audit_result, dict) else None)
    csv_path = write_review_queue_csv(rows, args.output_csv)
    md_path = write_review_queue_markdown(rows, args.output_md)

    print("CATALOG MANUAL REVIEW QUEUE EXPORTED")
    print(f"rows_exported: {len(rows)}")
    print(f"csv: {csv_path}")
    print(f"md: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
