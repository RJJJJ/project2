from __future__ import annotations

import json

from scripts.run_final_acceptance import (
    build_final_acceptance_steps,
    summarize_acceptance_results,
    write_final_acceptance_outputs,
)


def test_build_final_acceptance_steps_respects_skip_flags():
    steps = build_final_acceptance_steps(
        db_path="data/app_state/project2_dev.sqlite3",
        point_code="p001",
        output_dir="data/eval/final_acceptance",
        skip_pytest=True,
        skip_frontend_build=True,
    )
    by_name = {step.name: step for step in steps}
    assert by_name["pytest"].skipped is True
    assert by_name["frontend_build"].skipped is True
    assert any(step.kind == "smoke" for step in steps)


def test_summary_and_output_writer(tmp_path):
    results = [
        {"name": "pytest", "kind": "pytest", "status": "passed"},
        {"name": "regression", "kind": "regression", "status": "passed"},
        {"name": "smoke_sugar_shampoo", "kind": "smoke", "status": "passed", "smoke_check": {"detail": "status=ok"}},
        {"name": "smoke_nissin_brand", "kind": "smoke", "status": "passed", "smoke_check": {"detail": "query_type=brand_search"}},
        {"name": "confusion_audit", "kind": "confusion_audit", "status": "passed"},
        {"name": "frontend_build", "kind": "frontend_build", "status": "skipped"},
    ]
    summary = summarize_acceptance_results(results)
    assert summary["overall_status"] == "passed"
    assert summary["smoke_tests"]["passed"] == 2
    json_path, md_path = write_final_acceptance_outputs(tmp_path, results, summary)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["summary"]["overall_status"] == "passed"
    assert md_path.exists()

