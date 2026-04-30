import json

from services.query_review_queue import append_query_review_record, build_query_review_record


def test_build_query_review_record_flags_low_confidence():
    result = {
        "query": "未知商品",
        "status": "needs_clarification",
        "query_router": {"query_type": "unknown", "confidence": "low", "items": [{"raw": "未知商品"}], "reasons": ["no match"]},
        "candidate_summary": [],
        "diagnostics": {},
    }
    record = build_query_review_record(result)
    assert record["needs_review"] is True
    assert record["system_action"] == "clarify"
    assert record["raw_items"] == ["未知商品"]


def test_append_query_review_record_jsonl(tmp_path):
    path = tmp_path / "review.jsonl"
    record = {"query": "出前一丁", "needs_review": False}
    append_query_review_record(record, path)
    loaded = json.loads(path.read_text(encoding="utf-8").strip())
    assert loaded["query"] == "出前一丁"
