from __future__ import annotations

from scripts.run_agent_regression_pack import load_catalog_adversarial_cases, write_summary
from scripts.summarize_catalog_review_status import build_catalog_review_status_summary, write_catalog_review_status_markdown


def test_reviewed_case_loader_and_summary_counts(tmp_path):
    reviewed_cases_path = tmp_path / "reviewed.json"
    reviewed_cases_path.write_text(
        """
[
  {"case_id":"a1","query":"油","expected":{"status_in":["needs_clarification"]},"source":"catalog_confusion_audit","term":"油","needs_manual_label":false,"enforce":true,"status":"active"},
  {"case_id":"a2","query":"糖","expected":{"status_in":["needs_clarification"]},"source":"catalog_confusion_audit","term":"糖","needs_manual_label":true,"enforce":false,"status":"pending"},
  {"case_id":"a3","query":"雞蛋","expected":{"status":"not_covered"},"source":"catalog_confusion_audit","term":"雞蛋","needs_manual_label":true,"enforce":false,"status":"ignored"}
]
""".strip(),
        encoding="utf-8",
    )
    loaded = load_catalog_adversarial_cases(reviewed_cases_path)
    assert loaded[0]["enforce"] is True
    assert loaded[1]["pending_manual_label"] is True
    assert loaded[2]["status"] == "ignored"

    rows = [
        {"case_id": "base_1", "passed": True, "source": "base", "pending_manual_label": False, "ignored": False, "needs_revision": False, "needs_data_check": False},
        {"case_id": "a1", "passed": True, "source": "catalog_confusion_audit", "pending_manual_label": False, "ignored": False, "needs_revision": False, "needs_data_check": False, "catalog_state": "active_strict"},
        {"case_id": "a2", "passed": True, "source": "catalog_confusion_audit", "pending_manual_label": True, "ignored": False, "needs_revision": False, "needs_data_check": False, "catalog_state": "pending"},
        {"case_id": "a3", "passed": True, "source": "catalog_confusion_audit", "pending_manual_label": False, "ignored": True, "needs_revision": False, "needs_data_check": False, "catalog_state": "ignored"},
    ]
    summary_path = tmp_path / "summary.md"
    write_summary(summary_path, rows, {"planner_mode": "rule"})
    content = summary_path.read_text(encoding="utf-8")
    assert "active_strict: 1" in content
    assert "pending_manual_label: 1" in content
    assert "ignored: 1" in content


def test_review_status_summary_writes_markdown(tmp_path):
    cases = [
        {"case_id": "a1", "query": "油", "term": "油", "status": "active", "enforce": True, "needs_manual_label": False},
        {"case_id": "a2", "query": "糖", "term": "糖", "status": "pending", "enforce": False, "needs_manual_label": True},
        {"case_id": "a3", "query": "雞蛋", "term": "雞蛋", "status": "ignored", "enforce": False, "needs_manual_label": True},
    ]
    summary = build_catalog_review_status_summary(cases)
    assert summary["active_strict_cases"] == 1
    assert summary["pending_manual_labels"] == 1
    assert summary["ignored_cases"] == 1
    path = write_catalog_review_status_markdown(summary, tmp_path / "catalog_review_status_summary.md")
    assert path.exists()

