import json

from scripts.build_eval_cases_from_review_queue import build_eval_cases


def test_review_queue_eval_builder_deduplicates_and_marks_manual(tmp_path):
    path = tmp_path / "queue.jsonl"
    records = [
        {"query": "未知", "query_type": "unknown", "confidence": "low", "status": "needs_clarification", "needs_review": True},
        {"query": "未知", "query_type": "unknown", "confidence": "low", "status": "needs_clarification", "needs_review": True},
        {"query": "砂糖", "query_type": "category_search", "confidence": "high", "status": "ok", "needs_review": False},
    ]
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records), encoding="utf-8")
    cases = build_eval_cases(path)
    assert len(cases) == 1
    assert cases[0]["query"] == "未知"
    assert cases[0]["suggested_expected"]["needs_manual_label"] is True
