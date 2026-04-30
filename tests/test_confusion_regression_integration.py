from __future__ import annotations

import json

from scripts.run_agent_regression_pack import evaluate_case, load_catalog_adversarial_cases
from scripts.summarize_confusion_coverage import build_confusion_coverage_summary


def _result_with_products(*names: str) -> dict:
    return {
        "status": "needs_clarification",
        "ambiguous_items": [{"raw_item_name": "油"}],
        "not_covered_items": [],
        "resolved_items": [],
        "candidate_summary": [{"top_candidates": [{"product_name": name} for name in names]}],
        "price_plan": {},
        "query_router": {"query_type": "ambiguous_request", "confidence": "high"},
    }


def test_regression_pack_loads_catalog_adversarial_cases_and_skips_manual(tmp_path):
    cases_path = tmp_path / "catalog_adversarial_cases.json"
    payload = [
        {
            "case_id": "strict_oil",
            "term": "油",
            "query": "油",
            "expected": {"status_in": ["needs_clarification", "ambiguous"], "must_not_include_product_names": ["蠔油"]},
            "source": "catalog_confusion_audit",
            "needs_manual_label": False,
            "case_type": "generic_term_guardrail",
        },
        {
            "case_id": "manual_powder",
            "term": "粉",
            "query": "粉",
            "expected": {"status": "needs_clarification"},
            "source": "catalog_confusion_audit",
            "needs_manual_label": True,
            "case_type": "generic_term_guardrail",
        },
    ]
    cases_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    cases = load_catalog_adversarial_cases(cases_path)
    assert len(cases) == 2
    assert cases[0]["source"] == "catalog_confusion_audit"
    assert cases[1]["pending_manual_label"] is True


def test_regression_pack_enforces_include_and_exclude_product_names():
    case = {
        "case_id": "strict_oil",
        "query": "油",
        "expected": {"status_in": ["needs_clarification", "ambiguous"], "must_not_include_product_names": ["蠔油"]},
    }
    passed, failures, _ = evaluate_case(case, _result_with_products("花生油", "健康粟米油"))
    assert passed
    assert failures == []

    failed, failures, _ = evaluate_case(case, _result_with_products("花生油", "李錦記蠔油"))
    assert not failed
    assert any("should not contain 蠔油" in item for item in failures)


def test_confusion_coverage_summary_marks_protected_and_pending_terms():
    audit_result = {
        "terms": {
            "油": {"total_occurrences": 3, "by_risk_level": {"high": 2}, "manual_review_products": []},
            "糖": {"total_occurrences": 2, "by_risk_level": {"high": 1}, "manual_review_products": [{"product_name": "蜜糖"}]},
        }
    }
    regression_rows = [
        {"source": "catalog_confusion_audit", "term": "油", "passed": True, "pending_manual_label": False},
        {"source": "catalog_confusion_audit", "term": "糖", "passed": True, "pending_manual_label": True},
    ]
    summary = build_confusion_coverage_summary(audit_result, regression_rows)
    assert "油" in summary["terms_with_regression_protection"]
    assert "糖" in summary["terms_pending_manual_review"]
