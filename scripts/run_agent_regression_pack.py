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

from services.shopping_agent_orchestrator import run_shopping_agent
from services.sqlite_store import DEFAULT_DB_PATH


def _names(items: list[dict[str, Any]]) -> list[str]:
    return [str(item.get("raw_item_name") or "") for item in items]


def _resolved_intents(result: dict[str, Any]) -> list[str]:
    return [str(item.get("intent_id") or "") for item in result.get("resolved_items") or []]


def _candidate_text(result: dict[str, Any]) -> str:
    return json.dumps(result.get("candidate_summary") or [], ensure_ascii=False)


def _contains_any(values: list[str], needle: str) -> bool:
    return any(needle in value for value in values)


def _case(case_id: str, query: str, expected: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    return {"case_id": case_id, "query": query, "expected": expected, "overrides": overrides}


def build_cases(include_rag_cases: bool = True, include_local_llm_cases: bool = False) -> list[dict[str, Any]]:
    U = {
        "sugar": "\u7cd6", "white_sugar": "\u7802\u7cd6", "low_sugar_soy": "\u4f4e\u7cd6\u8c46\u5976",
        "oil": "\u6cb9", "cooking_oil": "\u98df\u6cb9", "sesame_noodle": "\u9ebb\u6cb9\u5473\u5373\u98df\u9eb5", "oyster_sauce": "\u8814\u6cb9",
        "noodle": "\u9eb5", "instant_noodle": "\u5373\u98df\u9eb5", "chocolate": "\u6731\u53e4\u529b", "chocolate_drink": "\u6731\u53e4\u529b\u98f2\u54c1",
        "tissue": "\u7d19\u5dfe", "wet_wipe": "\u6fd5\u7d19\u5dfe", "shampoo": "\u6d17\u982d\u6c34", "fries": "\u85af\u689d", "chips": "\u85af\u7247", "egg": "\u96de\u86cb", "egg_noodle": "\u96de\u86cb\u5e7c\u9762",
        "sauce1": "\u8fa3\u6912\u91ac", "sauce2": "\u9752\u82a5\u8fa3", "sauce3": "\u751c\u918b", "taikoo": "\u592a\u53e4\u7d14\u6b63\u7802\u7cd6",
    }
    cases = [
        _case("ambiguous_sugar", U["sugar"], {"status": "needs_clarification", "ambiguous_contains": [U["sugar"]]}),
        _case("resolved_sugar", U["white_sugar"], {"resolved_intents": ["cooking_sugar"], "not_candidate_contains": [U["low_sugar_soy"]], "price_plan_status_in": ["ok", "partial", "not_priceable"]}),
        _case("ambiguous_oil", U["oil"], {"status": "needs_clarification", "ambiguous_contains": [U["oil"]]}),
        _case("resolved_cooking_oil", U["cooking_oil"], {"resolved_intents": ["cooking_oil"], "not_candidate_contains": [U["sesame_noodle"], U["oyster_sauce"]]}),
        _case("ambiguous_noodle", U["noodle"], {"status": "needs_clarification", "ambiguous_contains": [U["noodle"]]}),
        _case("resolved_instant_noodle", U["instant_noodle"], {"resolved_intents": ["instant_noodle"]}),
        _case("ambiguous_chocolate", U["chocolate"], {"status": "needs_clarification", "ambiguous_contains": [U["chocolate"]]}),
        _case("resolved_chocolate_drink", U["chocolate_drink"], {"resolved_intents": ["chocolate_drink"]}),
        _case("ambiguous_tissue", U["tissue"], {"status": "needs_clarification", "ambiguous_contains": [U["tissue"]]}),
        _case("resolved_wet_wipe", U["wet_wipe"], {"resolved_intents": ["wet_wipe"]}),
        _case("resolved_shampoo", U["shampoo"], {"resolved_intents": ["shampoo"]}),
        _case("not_covered_mm", "M&M", {"status": "not_covered", "not_covered_contains": ["M&M"]}),
        _case("not_covered_fries", U["fries"], {"status": "not_covered", "not_covered_contains": [U["fries"]]}),
        _case("not_covered_eggs", U["egg"], {"status": "not_covered", "not_covered_contains": [U["egg"]], "not_candidate_contains": [U["egg_noodle"]]}),
        _case("mixed_guardrails", "\u5169\u5305\u9eb5 \u4e00\u5305\u85af\u689d \u56db\u5305\u85af\u7247 \u6cb9 \u7cd6 M&M", {"status": "needs_clarification", "ambiguous_contains": [U["noodle"], U["oil"], U["sugar"]], "not_covered_contains": [U["fries"], "M&M"], "resolved_contains": [U["chips"]]}),
        _case("ok_sugar_shampoo", "\u6211\u60f3\u8cb7\u7802\u7cd6\u540c\u6d17\u982d\u6c34", {"status": "ok", "resolved_contains": [U["white_sugar"], U["shampoo"]], "price_plan_status": "ok"}),
        _case("ok_oil_choc_toothpaste", "\u6211\u60f3\u8cb7\u98df\u6cb9\u3001\u6731\u53e4\u529b\u98f2\u54c1\u3001\u7259\u818f", {"status": "ok", "resolved_contains": [U["cooking_oil"], U["chocolate_drink"], "\u7259\u818f"], "price_plan_status": "ok"}),
    ]
    if include_rag_cases:
        cases.append(_case("rag_sugar_shampoo", "\u6211\u60f3\u8cb7\u6d17\u982d\u6c34\u540c\u7802\u7cd6", {"status": "ok", "resolved_contains": [U["white_sugar"], U["shampoo"]], "candidate_contains": [U["taikoo"]], "not_candidate_contains": [U["sauce1"], U["sauce2"], U["sauce3"]]}, retrieval_mode="rag_assisted"))
    if include_local_llm_cases:
        cases.append(_case("local_llm_fallback_sugar", U["white_sugar"], {"resolved_intents": ["cooking_sugar"]}, planner_mode="local_llm"))
    cases.extend(
        [
            _case("phase5_brand_nissin", "\u51fa\u524d\u4e00\u4e01", {"query_type": "brand_search", "not_status": ["needs_clarification", "not_covered"], "candidate_contains": ["\u51fa\u524d\u4e00\u4e01"]}),
            _case("phase5_nissin_sesame", "\u51fa\u524d\u4e00\u4e01\u9ebb\u6cb9\u5473", {"query_type_in": ["direct_product_search", "partial_product_search"], "top_candidate_contains": "\u9ebb\u6cb9\u5473", "top_candidate_not_contains": "\u4e5d\u5dde\u6fc3\u6e6f\u8c6c\u9aa8"}),
            _case("phase5_mak_lo_dai_egg_noodle", "\u9ea5\u8001\u5927\u96de\u86cb\u5e7c\u9762", {"query_type": "direct_product_search", "not_status": ["not_covered"], "top_candidate_contains": "\u9ea5\u8001\u5927\u96de\u86cb\u5e7c\u9762"}),
            _case("phase5_egg_not_covered", "\u96de\u86cb", {"query_type": "not_covered_request", "status": "not_covered", "not_candidate_contains": ["\u9ea5\u8001\u5927\u96de\u86cb\u5e7c\u9762"]}),
            _case("phase5_noodle_ambiguous", "\u9eb5", {"query_type": "ambiguous_request", "status": "needs_clarification"}),
            _case("phase5_noodle_simplified_ambiguous", "\u9762", {"query_type": "ambiguous_request", "status": "needs_clarification"}),
            _case("phase5_subjective_noodle", "\u6700\u597d\u5403\u7684\u9eb5", {"query_type_in": ["subjective_recommendation", "unsupported_request"], "status": "unsupported"}),
            _case("phase5_cheapest_nissin", "\u6700\u4fbf\u5b9c\u7684\u51fa\u524d\u4e00\u4e01", {"query_type": "brand_search", "candidate_contains": ["\u51fa\u524d\u4e00\u4e01"]}),
            _case("phase5_vitasoy_brand", "\u7dad\u4ed6\u5976", {"query_type": "brand_search", "candidate_contains": ["\u7dad\u4ed6\u5976"], "not_candidate_contains": ["forced_low_sugar_marker"]}),
            _case("phase5_vitasoy_low_sugar", "\u7dad\u4ed6\u5976\u4f4e\u7cd6\u8c46\u5976", {"query_type_in": ["direct_product_search", "partial_product_search"], "top_candidate_contains": "\u7dad\u4ed6\u5976\u4f4e\u7cd6\u8c46\u5976"}),
            _case("phase6_bb_wet_wipe", "BB用嘅\u6fd5\u7d19\u5dfe", {"query_type_in": ["category_search", "partial_product_search", "direct_product_search"], "not_candidate_contains": ["forced_tissue_marker"]}),
            _case("phase6_cheapest_nissin", "\u6700\u4fbf\u5b9c\u7684\u51fa\u524d\u4e00\u4e01", {"query_type": "brand_search", "candidate_contains": ["\u51fa\u524d\u4e00\u4e01"]}),
            _case("phase6_vitasoy_low_sugar", "\u7dad\u4ed6\u5976\u4f4e\u7cd6\u8c46\u5976", {"query_type_in": ["direct_product_search", "partial_product_search"], "top_candidate_contains": "\u7dad\u4ed6\u5976\u4f4e\u7cd6\u8c46\u5976"}),
            _case("phase6_health_drink", "\u6700\u5065\u5eb7\u7684\u98f2\u54c1", {"query_type_in": ["subjective_recommendation", "unsupported_request"], "status": "unsupported"}),
        ]
    )
    return cases


def load_extra_cases(path: str | None) -> list[dict[str, Any]]:
    if not path:
        return []
    extra_path = Path(path)
    if not extra_path.exists():
        return []
    data = json.loads(extra_path.read_text(encoding="utf-8"))
    cases: list[dict[str, Any]] = []
    for idx, item in enumerate(data if isinstance(data, list) else []):
        query = str(item.get("query") or "").strip()
        if not query:
            continue
        expected = item.get("suggested_expected") or {}
        cases.append({"case_id": f"review_queue_{idx + 1}", "query": query, "expected": expected, "overrides": {}, "pending_manual_label": bool(expected.get("needs_manual_label"))})
    return cases


def evaluate_case(case: dict[str, Any], result: dict[str, Any]) -> tuple[bool, list[str], dict[str, Any]]:
    expected = case["expected"]
    failures: list[str] = []
    ambiguous = _names(result.get("ambiguous_items") or [])
    not_covered = _names(result.get("not_covered_items") or [])
    resolved = _names(result.get("resolved_items") or [])
    intents = _resolved_intents(result)
    candidate_text = _candidate_text(result)
    price_plan = result.get("price_plan") or {}
    router = result.get("query_router") or {}
    if expected.get("status") and result.get("status") != expected["status"]:
        failures.append(f"status expected {expected['status']} got {result.get('status')}")
    if expected.get("not_status") and result.get("status") in expected["not_status"]:
        failures.append(f"status should not be in {expected['not_status']} got {result.get('status')}")
    if expected.get("query_type") and router.get("query_type") != expected["query_type"]:
        failures.append(f"query_type expected {expected['query_type']} got {router.get('query_type')}")
    if expected.get("query_type_in") and router.get("query_type") not in expected["query_type_in"]:
        failures.append(f"query_type expected in {expected['query_type_in']} got {router.get('query_type')}")
    if expected.get("price_plan_status") and price_plan.get("status") != expected["price_plan_status"]:
        failures.append(f"price_plan.status expected {expected['price_plan_status']} got {price_plan.get('status')}")
    if expected.get("price_plan_status_in") and price_plan.get("status") not in expected["price_plan_status_in"]:
        failures.append(f"price_plan.status expected in {expected['price_plan_status_in']} got {price_plan.get('status')}")
    for needle in expected.get("ambiguous_contains", []):
        if not _contains_any(ambiguous, needle):
            failures.append(f"ambiguous missing {needle}")
    for needle in expected.get("not_covered_contains", []):
        if not _contains_any(not_covered, needle):
            failures.append(f"not_covered missing {needle}")
    for needle in expected.get("resolved_contains", []):
        if not _contains_any(resolved, needle):
            failures.append(f"resolved missing {needle}")
    for intent in expected.get("resolved_intents", []):
        if intent not in intents:
            failures.append(f"intent missing {intent}")
    for needle in expected.get("candidate_contains", []):
        if needle not in candidate_text:
            failures.append(f"candidate text missing {needle}")
    for needle in expected.get("not_candidate_contains", []):
        if needle in candidate_text:
            failures.append(f"candidate text should not contain {needle}")
    if expected.get("top_candidate_contains") or expected.get("top_candidate_not_contains"):
        top_candidate = ""
        summaries = result.get("candidate_summary") or []
        if summaries and (summaries[0].get("top_candidates") or []):
            top_candidate = str(summaries[0]["top_candidates"][0].get("product_name") or "")
        if expected.get("top_candidate_contains") and expected["top_candidate_contains"] not in top_candidate:
            failures.append(f"top candidate missing {expected['top_candidate_contains']} got {top_candidate}")
        if expected.get("top_candidate_not_contains") and expected["top_candidate_not_contains"] in top_candidate:
            failures.append(f"top candidate should not contain {expected['top_candidate_not_contains']} got {top_candidate}")
    actual_summary = {
        "status": result.get("status"),
        "resolved": resolved,
        "resolved_intents": intents,
        "ambiguous": ambiguous,
        "not_covered": not_covered,
        "price_plan_status": price_plan.get("status"),
        "decision_policy": (price_plan.get("decision_result") or {}).get("policy"),
        "query_type": router.get("query_type"),
        "query_confidence": router.get("confidence"),
    }
    return not failures, failures, actual_summary


def write_summary(path: Path, rows: list[dict[str, Any]], modes: dict[str, Any]) -> None:
    total = len(rows)
    passed = sum(1 for row in rows if row["passed"])
    pending = sum(1 for row in rows if row.get("pending_manual_label"))
    failed = total - passed
    pass_rate = 0 if total == 0 else round(passed / total * 100, 2)
    failed_rows = [row for row in rows if not row["passed"]]
    lines = [
        "# Agent Regression Summary",
        "",
        f"generated_at: {datetime.now(timezone.utc).isoformat()}",
        f"total: {total}",
        f"passed: {passed}",
        f"failed: {failed}",
        f"pending_manual_label: {pending}",
        f"pass_rate: {pass_rate}%",
        f"modes used: `{json.dumps(modes, ensure_ascii=False)}`",
        "",
        "## Failed cases",
    ]
    if failed_rows:
        for row in failed_rows:
            lines.append(f"- {row['case_id']}: {'; '.join(row['failures'])}")
    else:
        lines.append("- none")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Project2 shopping agent regression pack.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--point-code", default="p001")
    parser.add_argument("--output-dir", default="data/eval")
    parser.add_argument("--planner-mode", default="rule", choices=["rule", "local_llm"])
    parser.add_argument("--retrieval-mode", default="taxonomy", choices=["taxonomy", "rag_assisted", "rag_v2"])
    parser.add_argument("--composer-mode", default="template", choices=["template", "gemini"])
    parser.add_argument("--llm-router-enabled", action="store_true")
    parser.add_argument("--llm-router-provider", default="gemini", choices=["gemini", "local_llm"])
    parser.add_argument("--llm-router-model", default=None)
    parser.add_argument("--decision-policy", default="cheapest_single_store", choices=["cheapest_single_store", "cheapest_two_stores", "single_store_preferred", "balanced"])
    parser.add_argument("--include-rag-cases", action="store_true")
    parser.add_argument("--include-local-llm-cases", action="store_true")
    parser.add_argument("--extra-cases-path", default=None)
    args = parser.parse_args()

    include_rag = True or args.include_rag_cases
    cases = build_cases(include_rag_cases=include_rag, include_local_llm_cases=args.include_local_llm_cases)
    cases.extend(load_extra_cases(args.extra_cases_path))
    rows: list[dict[str, Any]] = []
    for case in cases:
        if case.get("pending_manual_label"):
            rows.append({"case_id": case["case_id"], "query": case["query"], "passed": True, "pending_manual_label": True, "expected": case["expected"], "actual_summary": {}, "failures": []})
            continue
        overrides = dict(case.get("overrides") or {})
        result = run_shopping_agent(
            case["query"],
            Path(args.db_path),
            point_code=args.point_code,
            include_price_plan=True,
            planner_mode=overrides.get("planner_mode", args.planner_mode),
            retrieval_mode=overrides.get("retrieval_mode", args.retrieval_mode),
            composer_mode=args.composer_mode,
            decision_policy=args.decision_policy,
            llm_router_enabled=args.llm_router_enabled,
            llm_router_provider=args.llm_router_provider,
            llm_router_model=args.llm_router_model,
        )
        passed, failures, actual_summary = evaluate_case(case, result)
        rows.append({"case_id": case["case_id"], "query": case["query"], "passed": passed, "expected": case["expected"], "actual_summary": actual_summary, "failures": failures})

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results_path = output_dir / "agent_regression_results.json"
    summary_path = output_dir / "agent_regression_summary.md"
    results_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    modes = {"planner_mode": args.planner_mode, "retrieval_mode": args.retrieval_mode, "composer_mode": args.composer_mode, "decision_policy": args.decision_policy, "llm_router_enabled": args.llm_router_enabled}
    write_summary(summary_path, rows, modes)
    total = len(rows)
    passed = sum(1 for row in rows if row["passed"])
    pending = sum(1 for row in rows if row.get("pending_manual_label"))
    failed = total - passed
    pass_rate = 0 if total == 0 else round(passed / total * 100, 2)
    print("AGENT REGRESSION SUMMARY")
    print(f"total: {total}")
    print(f"passed: {passed}")
    print(f"failed: {failed}")
    print(f"pending_manual_label: {pending}")
    print(f"pass_rate: {pass_rate}%")
    print("outputs:")
    print(f"- {results_path}")
    print(f"- {summary_path}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
