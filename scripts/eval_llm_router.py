from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from services.llm_query_router import merge_rule_and_llm_router_outputs, route_query_with_llm
from services.query_intent_router import route_user_query


CASES = [
    {"query": "出前一丁", "expected": ["brand_search"]},
    {"query": "出前一丁麻油味", "expected": ["partial_product_search", "direct_product_search"]},
    {"query": "麥老大雞蛋幼面", "expected": ["direct_product_search"]},
    {"query": "雞蛋", "expected": ["not_covered_request"]},
    {"query": "最好吃的麵", "expected": ["subjective_recommendation", "unsupported_request"]},
    {"query": "糖", "expected": ["ambiguous_request"]},
    {"query": "油", "expected": ["ambiguous_request"]},
    {"query": "BB用嘅濕紙巾", "expected": ["category_search", "partial_product_search"]},
    {"query": "維他奶低糖豆奶", "expected": ["direct_product_search", "partial_product_search"]},
    {"query": "最便宜的出前一丁", "expected": ["brand_search"], "goal": "cheapest"},
]


def _guardrail_violation(query: str, query_type: str) -> str | None:
    if query == "雞蛋" and query_type in {"direct_product_search", "partial_product_search", "brand_search", "category_search"}:
        return "egg_overridden"
    if query in {"糖", "油"} and query_type in {"direct_product_search", "partial_product_search"}:
        return "short_ambiguous_direct"
    if query == "最好吃的麵" and query_type in {"category_search", "direct_product_search", "partial_product_search"}:
        return "subjective_priced"
    if query.upper() == "M&M" and query_type != "not_covered_request":
        return "mm_chocolate_mapped"
    return None


def evaluate(provider: str, model: str | None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    fallback_count = 0
    invalid_json_count = 0
    guardrail_violations = 0
    exact = 0
    acceptable = 0
    provider_unavailable = False
    for case in CASES:
        rule = route_user_query(case["query"])
        llm, diag = route_query_with_llm(case["query"], provider=provider, model=model, timeout_seconds=10)
        if diag.get("llm_router_used") == "fallback":
            fallback_count += 1
            provider_unavailable = True
        if diag.get("llm_router_errors") and not llm:
            invalid_json_count += 1 if "JSON" in ";".join(diag.get("llm_router_errors") or []) else 0
        merged = merge_rule_and_llm_router_outputs(rule, llm, strategy="guarded")
        actual = str(merged.get("query_type") or "unknown")
        expected = case["expected"]
        if actual == expected[0]:
            exact += 1
        if actual in expected:
            acceptable += 1
        violation = _guardrail_violation(case["query"], actual)
        if violation:
            guardrail_violations += 1
        rows.append(
            {
                "query": case["query"],
                "expected": expected,
                "actual_query_type": actual,
                "confidence": merged.get("confidence"),
                "llm_router_used": diag.get("llm_router_used"),
                "errors": diag.get("llm_router_errors") or [],
                "guardrail_violation": violation,
                "passed": actual in expected and not violation,
            }
        )
    total = len(rows)
    passed = sum(1 for row in rows if row["passed"])
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "model": model,
        "total": total,
        "exact_query_type_match": exact,
        "acceptable_match": acceptable,
        "guardrail_violations": guardrail_violations,
        "fallback_count": fallback_count,
        "invalid_json_count": invalid_json_count,
        "pass_rate": round((passed / total * 100) if total else 0, 2),
        "provider_unavailable": provider_unavailable,
    }
    return rows, summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate LLM router against guardrail cases.")
    parser.add_argument("--db-path", default="data/app_state/project2_dev.sqlite3")
    parser.add_argument("--provider", default="gemini", choices=["gemini", "local_llm"])
    parser.add_argument("--model", default=None)
    parser.add_argument("--output-dir", default="data/eval")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    rows, summary = evaluate(args.provider, args.model)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results_path = output_dir / "llm_router_eval_results.json"
    summary_path = output_dir / "llm_router_eval_summary.md"
    results_path.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# LLM Router Eval Summary",
        "",
        *[f"{key}: {value}" for key, value in summary.items()],
        "",
        "## Failed / fallback cases",
    ]
    for row in rows:
        if not row["passed"] or row["llm_router_used"] == "fallback":
            lines.append(f"- {row['query']}: actual={row['actual_query_type']} expected={row['expected']} used={row['llm_router_used']} errors={row['errors']}")
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("LLM ROUTER EVAL SUMMARY")
    for key, value in summary.items():
        print(f"{key}: {value}")
    print(f"outputs: {results_path}, {summary_path}")
    if args.strict and (summary["guardrail_violations"] or summary["provider_unavailable"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
