from __future__ import annotations

from datetime import datetime

import scripts.verify_demo_points as verifier


def _write_fake_processed(processed_root, date: str, point_code: str) -> None:
    point_dir = processed_root / date / point_code
    point_dir.mkdir(parents=True)
    (point_dir / "category_1_prices.jsonl").write_text('{"product_name": "米"}\n', encoding="utf-8")


def test_verify_point_with_processed_data_sets_basket_ok(monkeypatch, tmp_path) -> None:
    _write_fake_processed(tmp_path, "2026-04-25", "p001")

    monkeypatch.setattr(
        verifier,
        "build_result",
        lambda *args, **kwargs: {
            "plans": [{"plan_type": "cheapest_by_item", "estimated_total_mop": 12.0}],
            "recommended_plan_type": "cheapest_by_item",
            "warnings": [],
        },
    )
    monkeypatch.setattr(
        verifier,
        "analyze_point_signals",
        lambda *args, **kwargs: {"largest_price_gap": [{"product_name": "米"}]},
    )

    summary = verifier.verify_point({"point_code": "p001", "name": "高士德", "district": "澳門半島"}, processed_root=tmp_path)

    assert summary["has_processed_data"] is True
    assert summary["basket_ok"] is True
    assert summary["basket_total"] == 12.0
    assert summary["recommended_plan_type"] == "cheapest_by_item"
    assert summary["signals_ok"] is True
    assert summary["largest_gap_count"] == 1


def test_verify_point_without_processed_data_sets_has_processed_data_false(tmp_path) -> None:
    summary = verifier.verify_point({"point_code": "p002", "name": "缺資料", "district": "澳門半島"}, processed_root=tmp_path)

    assert summary["has_processed_data"] is False
    assert summary["basket_ok"] is False
    assert summary["signals_ok"] is False
    assert summary["errors"] == ["processed data not found"]


def test_markdown_report_can_be_generated(tmp_path) -> None:
    summaries = [
        {
            "point_code": "p001",
            "name": "高士德",
            "district": "澳門半島",
            "has_processed_data": True,
            "basket_ok": True,
            "basket_total": 12.0,
            "recommended_plan_type": "cheapest_by_item",
            "signals_ok": True,
            "largest_gap_count": 2,
            "warnings": [],
            "errors": [],
        }
    ]
    report = verifier.build_markdown_report(
        summaries,
        text="我想買一包米",
        generated_at=datetime(2026, 4, 25, 12, 0, 0),
    )
    report_path = verifier.write_markdown_report(summaries, report_path=tmp_path / "POINT_TEST_REPORT.md")

    assert "# 多地區 MVP 驗收報告" in report
    assert "p001" in report
    assert report_path.exists()
    assert "每個 point 的結果" in report_path.read_text(encoding="utf-8")
