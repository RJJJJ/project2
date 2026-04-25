from __future__ import annotations

import scripts.dev_check as dev_check


def test_dev_check_summary_can_be_generated() -> None:
    summary = dev_check.build_summary()

    assert {
        "python_ok",
        "packages_ok",
        "processed_data_ok",
        "latest_processed_date",
        "collection_points_count",
        "api_import_ok",
        "frontend_ok",
        "errors",
    }.issubset(summary)
    assert isinstance(summary["errors"], list)
