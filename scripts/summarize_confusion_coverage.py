from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def _load_json(path: str | Path) -> dict | list:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_confusion_coverage_summary(audit_result: dict, regression_rows: list[dict]) -> dict:
    audited_terms = list((audit_result.get("terms") or {}).keys())
    adversarial_rows = [row for row in regression_rows if row.get("source") == "catalog_confusion_audit"]
    terms_with_adversarial_cases = sorted({str(row.get("term") or "") for row in adversarial_rows if row.get("term")})
    protected_terms = sorted(
        {
            str(row.get("term") or "")
            for row in adversarial_rows
            if row.get("term") and row.get("passed") and not row.get("pending_manual_label")
        }
    )
    pending_manual_terms = sorted(
        {
            str(row.get("term") or "")
            for row in adversarial_rows
            if row.get("term") and row.get("pending_manual_label")
        }
    )
    uncovered_risks: list[dict] = []
    for term, info in (audit_result.get("terms") or {}).items():
        high_risk_count = int((info.get("by_risk_level") or {}).get("high", 0))
        manual_review_count = len(info.get("manual_review_products") or [])
        if term in protected_terms:
            continue
        uncovered_risks.append(
            {
                "term": term,
                "high_risk_count": high_risk_count,
                "manual_review_count": manual_review_count,
                "total_occurrences": int(info.get("total_occurrences") or 0),
            }
        )
    uncovered_risks.sort(key=lambda item: (-item["high_risk_count"], -item["manual_review_count"], -item["total_occurrences"], item["term"]))
    return {
        "audited_terms": audited_terms,
        "terms_with_adversarial_cases": terms_with_adversarial_cases,
        "terms_with_regression_protection": protected_terms,
        "terms_pending_manual_review": pending_manual_terms,
        "top_uncovered_risks": uncovered_risks[:10],
    }


def _markdown(summary: dict) -> str:
    lines = [
        "# Confusion Coverage Summary",
        "",
        "## Terms audited",
    ]
    lines.extend([f"- {term}" for term in summary.get("audited_terms") or []] or ["- none"])
    lines.extend(["", "## Terms with adversarial cases"])
    lines.extend([f"- {term}" for term in summary.get("terms_with_adversarial_cases") or []] or ["- none"])
    lines.extend(["", "## Terms with regression protection"])
    lines.extend([f"- {term}" for term in summary.get("terms_with_regression_protection") or []] or ["- none"])
    lines.extend(["", "## Terms pending manual review"])
    lines.extend([f"- {term}" for term in summary.get("terms_pending_manual_review") or []] or ["- none"])
    lines.extend(["", "## Top 10 uncovered risks"])
    uncovered = summary.get("top_uncovered_risks") or []
    if uncovered:
        for item in uncovered:
            lines.append(
                f"- {item['term']}: high_risk={item['high_risk_count']}, "
                f"manual_review={item['manual_review_count']}, occurrences={item['total_occurrences']}"
            )
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize confusion-audit regression coverage.")
    parser.add_argument("--audit-path", required=True)
    parser.add_argument("--regression-results", required=True)
    parser.add_argument("--output-path", required=True)
    args = parser.parse_args()

    audit_result = _load_json(args.audit_path)
    regression_rows = _load_json(args.regression_results)
    summary = build_confusion_coverage_summary(audit_result, regression_rows if isinstance(regression_rows, list) else [])

    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_markdown(summary), encoding="utf-8")
    print(f"output: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
