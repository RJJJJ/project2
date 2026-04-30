from scripts.eval_llm_router import evaluate


def test_eval_llm_router_handles_missing_provider_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    rows, summary = evaluate("gemini", "gemini-2.5-flash")
    assert rows
    assert summary["provider_unavailable"] is True
    assert summary["guardrail_violations"] == 0
