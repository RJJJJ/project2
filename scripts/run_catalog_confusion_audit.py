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

from services.catalog_confusion_audit import (
    audit_confusion_terms,
    build_confusion_summary,
    generate_adversarial_cases_from_audit,
    load_catalog_for_confusion_audit,
)


def _parse_terms(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    return [term.strip() for term in raw.split(",") if term.strip()]


def _trim_audit_result(audit_result: dict, max_products_per_term: int) -> dict:
    trimmed = json.loads(json.dumps(audit_result, ensure_ascii=False))
    for info in (trimmed.get("terms") or {}).values():
        info["high_risk_products"] = (info.get("high_risk_products") or [])[:max_products_per_term]
        info["manual_review_products"] = (info.get("manual_review_products") or [])[:max_products_per_term]
    return trimmed


def _summary_markdown(summary: dict, audit_result: dict, adversarial_cases: list[dict]) -> str:
    lines = [
        "# Catalog Confusion Audit Summary",
        "",
        f"- generated_at: {summary.get('generated_at')}",
        f"- products_total: {summary.get('products_total')}",
        f"- terms_total: {summary.get('terms_total')}",
        f"- high_risk_occurrence_count: {summary.get('high_risk_occurrence_count')}",
        f"- manual_review_count: {summary.get('manual_review_count')}",
        f"- adversarial_cases_total: {len(adversarial_cases)}",
        "",
        "## Top risky terms",
    ]
    top_terms = summary.get("top_risky_terms") or []
    if top_terms:
        for item in top_terms:
            lines.append(
                f"- {item['term']}: occurrences={item['total_occurrences']}, "
                f"high_risk={item['high_risk_count']}, manual_review={item['manual_review_count']}, "
                f"risk_score={item['risk_score']}"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## High risk products"])
    added = False
    for term, info in (audit_result.get("terms") or {}).items():
        for product in (info.get("high_risk_products") or [])[:5]:
            lines.append(
                f"- [{term}] {product.get('product_name')} "
                f"({product.get('occurrence_type')}; {product.get('suggested_guardrail')})"
            )
            added = True
    if not added:
        lines.append("- none")
    lines.extend(["", "## Suggested regression additions"])
    if adversarial_cases:
        for case in adversarial_cases[:20]:
            lines.append(
                f"- {case.get('case_id')}: query={case.get('query')} "
                f"(manual={case.get('needs_manual_label')}, type={case.get('case_type')})"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Terms needing manual review"])
    manual_terms = summary.get("terms_needing_manual_review") or []
    if manual_terms:
        for term in manual_terms:
            lines.append(f"- {term}")
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Project2 catalog-wide confusion audit.")
    parser.add_argument("--db-path", required=True)
    parser.add_argument("--output-dir", default="data/eval")
    parser.add_argument("--terms", default=None)
    parser.add_argument("--max-products-per-term", type=int, default=100)
    parser.add_argument("--generate-adversarial-cases", action="store_true")
    parser.add_argument("--adversarial-output", default=None)
    args = parser.parse_args()

    products = load_catalog_for_confusion_audit(args.db_path)
    audit_result = audit_confusion_terms(products, terms=_parse_terms(args.terms))
    summary = build_confusion_summary(audit_result)
    adversarial_cases = generate_adversarial_cases_from_audit(audit_result) if args.generate_adversarial_cases else []

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    audit_path = output_dir / "catalog_confusion_audit.json"
    summary_path = output_dir / "catalog_confusion_audit_summary.md"
    adversarial_path = Path(args.adversarial_output) if args.adversarial_output else output_dir / "catalog_adversarial_cases.json"

    trimmed_audit_result = _trim_audit_result(audit_result, max(1, args.max_products_per_term))
    audit_path.write_text(json.dumps(trimmed_audit_result, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_path.write_text(_summary_markdown(summary, trimmed_audit_result, adversarial_cases), encoding="utf-8")
    if args.generate_adversarial_cases:
        adversarial_path.write_text(json.dumps(adversarial_cases, ensure_ascii=False, indent=2), encoding="utf-8")

    print("CATALOG CONFUSION AUDIT")
    print(f"products_total: {summary['products_total']}")
    print(f"terms_total: {summary['terms_total']}")
    print(f"high_risk_occurrence_count: {summary['high_risk_occurrence_count']}")
    print(f"manual_review_count: {summary['manual_review_count']}")
    print("outputs:")
    print(f"- {audit_path}")
    print(f"- {summary_path}")
    if args.generate_adversarial_cases:
        print(f"- {adversarial_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
