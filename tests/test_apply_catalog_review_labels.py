from __future__ import annotations

from scripts.apply_catalog_review_labels import apply_review_labels_to_cases


def test_apply_promote_and_pending_and_ignore():
    cases = [
        {"case_id": "c1", "query": "油", "needs_manual_label": True},
        {"case_id": "c2", "query": "糖", "needs_manual_label": True},
        {"case_id": "c3", "query": "雞蛋", "needs_manual_label": True},
        {"case_id": "c4", "query": "米", "needs_manual_label": True},
    ]
    review_rows = [
        {"case_id": "c1", "review_decision": "promote_to_strict", "review_notes": "safe", "reviewer": "qa", "reviewed_at": "2026-04-30"},
        {"case_id": "c2", "review_decision": "keep_pending", "review_notes": "", "reviewer": "", "reviewed_at": ""},
        {"case_id": "c3", "review_decision": "ignore_case", "review_notes": "", "reviewer": "", "reviewed_at": ""},
        {"case_id": "c4", "review_decision": "", "review_notes": "", "reviewer": "", "reviewed_at": ""},
    ]
    reviewed_cases, counters = apply_review_labels_to_cases(cases, review_rows)
    by_id = {case["case_id"]: case for case in reviewed_cases}

    assert by_id["c1"]["needs_manual_label"] is False
    assert by_id["c1"]["enforce"] is True
    assert by_id["c1"]["status"] == "active"

    assert by_id["c2"]["needs_manual_label"] is True
    assert by_id["c2"]["enforce"] is False
    assert by_id["c2"]["status"] == "pending"

    assert by_id["c3"]["status"] == "ignored"
    assert by_id["c3"]["enforce"] is False

    assert "status" not in by_id["c4"]
    assert counters["promoted_to_strict"] == 1
    assert counters["kept_pending"] == 1
    assert counters["ignored"] == 1
    assert counters["unchanged"] == 1

