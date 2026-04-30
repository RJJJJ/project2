from __future__ import annotations

import csv

from scripts.export_catalog_review_queue import CSV_COLUMNS, build_catalog_review_queue_rows, write_review_queue_csv, write_review_queue_markdown


def test_export_review_queue_only_includes_pending_cases(tmp_path):
    cases = [
        {
            "case_id": "pending_1",
            "query": "油",
            "term": "油",
            "source": "catalog_confusion_audit",
            "expected": {"status_in": ["needs_clarification"], "must_not_include_product_names": ["蠔油"]},
            "needs_manual_label": True,
            "case_type": "generic_term_guardrail",
        },
        {
            "case_id": "strict_1",
            "query": "糖",
            "term": "糖",
            "source": "catalog_confusion_audit",
            "expected": {"status_in": ["needs_clarification"]},
            "needs_manual_label": False,
            "case_type": "generic_term_guardrail",
        },
    ]
    rows = build_catalog_review_queue_rows(cases, {})
    assert len(rows) == 1
    assert rows[0]["case_id"] == "pending_1"
    assert set(CSV_COLUMNS).issubset(rows[0].keys())

    csv_path = write_review_queue_csv(rows, tmp_path / "queue.csv")
    md_path = write_review_queue_markdown(rows, tmp_path / "queue.md")
    assert csv_path.exists()
    assert md_path.exists()
    with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
        saved_rows = list(csv.DictReader(fh))
    assert saved_rows[0]["review_decision"] == ""
    assert "suggested_review_decision" in saved_rows[0]

