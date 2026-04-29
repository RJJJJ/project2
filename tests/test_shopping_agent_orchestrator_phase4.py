from pathlib import Path

import pytest

from services.shopping_agent_orchestrator import run_shopping_agent
from services.sqlite_store import DEFAULT_DB_PATH


def test_orchestrator_balanced_returns_decision_result():
    db = Path(DEFAULT_DB_PATH)
    if not db.exists():
        pytest.skip("local sqlite demo database not available")
    result = run_shopping_agent("?????????", db, point_code="p001", include_price_plan=True, decision_policy="balanced")
    assert "price_plan" in result
    assert result["price_plan"]["decision_result"]["policy"] == "balanced"
    assert "decision_result" in result["price_plan"]
