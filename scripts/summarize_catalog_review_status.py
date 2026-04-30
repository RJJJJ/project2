from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def _load_cases(path: str | Path) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def build_catalog_review_status_summary(cases: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts = Counter(str(case.get("status") or ("pending" if case.get("needs_manual_label") else "active")) for case in cases)
    by_risk_term = Counter(str(case.get("term") or "") for case in cases)
    promoted = [case for case in cases if str(case.get("status") or "") == "active" and (case.get("enforce") is True or not case.get("needs_manual_label"))]
    pending = [case for case in cases if str(case.get("status") or "pending") == "pending" or (case.get("needs_manual_label") and not case.get("status"))]
    ignored = [case for case in cases if str(case.get("status") or "") == "ignored"]
    return {
        "total_cases": len(cases),
        "active_strict_cases": status_counts.get("active", 0),
        "pending_manual_labels": status_counts.get("pending", 0) + sum(1 for case in cases if case.get("needs_manual_label") and not case.get("status")),
        "ignored_cases": status_counts.get("ignored", 0),
        "needs_revision": status_counts.get("needs_revision", 0),
        "needs_data_check": status_counts.get("needs_data_check", 0),
        "by_risk_term": dict(sorted(by_risk_term.items())),
        "promoted_cases": promoted,
        "pending_cases": pending,
        "ignored_case_list": ignored,
    }


def write_catalog_review_status_markdown(summary: dict[str, Any], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Catalog Review Status Summary",
        "",
        f"- total cases: {summary['total_cases']}",
        f"- active strict cases: {summary['active_strict_cases']}",
        f"- pending manual labels: {summary['pending_manual_labels']}",
        f"- ignored cases: {summary['ignored_cases']}",
        f"- needs revision: {summary['needs_revision']}",
        f"- needs data check: {summary['needs_data_check']}",
        "",
        "## By risk_term breakdown",
    ]
    lines.extend([f"- {term or '(blank)'}: {count}" for term, count in summary["by_risk_term"].items()] or ["- none"])
    lines.extend(["", "## Promoted cases list"])
    lines.extend([f"- {case.get('case_id')}: {case.get('query')}" for case in summary["promoted_cases"]] or ["- none"])
    lines.extend(["", "## Pending cases list"])
    lines.extend([f"- {case.get('case_id')}: {case.get('query')}" for case in summary["pending_cases"]] or ["- none"])
    lines.extend(["", "## Ignored cases list"])
    lines.extend([f"- {case.get('case_id')}: {case.get('query')}" for case in summary["ignored_case_list"]] or ["- none"])
    lines.extend(
        [
            "",
            "## Recommended next actions",
            "- Promote stable generic-term guardrail cases into strict reviewed coverage.",
            "- Keep product-name edge cases pending until expected behavior is manually confirmed.",
            "- Move `needs_revision` cases into a small JSON-edit queue or issue tracker.",
            "- Investigate `needs_data_check` cases against the source catalog before promotion.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize reviewed catalog adversarial case status.")
    parser.add_argument("--cases-path", required=True)
    parser.add_argument("--output-path", required=True)
    args = parser.parse_args()

    cases = _load_cases(args.cases_path)
    summary = build_catalog_review_status_summary(cases)
    output_path = write_catalog_review_status_markdown(summary, args.output_path)
    print(f"output: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
