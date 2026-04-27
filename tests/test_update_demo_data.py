from __future__ import annotations

import json
from pathlib import Path

from scripts import update_demo_data as updater


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def _write_fake_processed(root: Path, date: str = "2026-04-25", point_code: str = "p001") -> Path:
    point_dir = root / date / point_code
    _write_jsonl(point_dir / "supermarkets.jsonl", [{"supermarket_oid": 1, "supermarket_name": "Store A"}])
    _write_jsonl(
        point_dir / "category_1_prices.jsonl",
        [{"product_oid": 10, "supermarket_oid": 1, "price_mop": 12.0, "category_id": 1}],
    )
    return point_dir


def _fake_basket(date: str, point_code: str, text: str, processed_root: Path) -> dict:
    return {
        "plans": [
            {
                "plan_type": "cheapest_by_item",
                "estimated_total_mop": 12.0,
                "items": [{"product_oid": 10, "product_name": "Rice"}],
            }
        ],
        "recommended_plan_type": "cheapest_by_item",
        "warnings": [],
    }


def _fake_signals(date: str, point_code: str, processed_root: Path) -> dict:
    return {"largest_price_gap": [{"product_oid": 10}]}


def _fake_historical_signals(**kwargs) -> dict:
    return {"signals": [{"product_oid": 10}], "warnings": ["sample warning"]}


def _fake_watchlist_alerts(**kwargs) -> dict:
    return {
        "alerts": [{"product_oid": 10}],
        "summary": {"alerts_count": 1, "notify_count": 1},
        "warnings": ["alert warning"],
    }


def test_report_summary_can_be_generated() -> None:
    points = [
        {
            "point_code": "p001",
            "fetch_ok": True,
            "validation_ok": True,
            "basket_ok": True,
            "signals_ok": True,
            "historical_signals_ok": True,
            "watchlist_alerts_ok": True,
        }
    ]

    report = updater.build_update_report(
        points=points,
        date_value="2026-04-25",
        preset="demo_daily",
        max_points=5,
        sync_demo_data=True,
        generated_at="2026-04-25T00:00:00+00:00",
    )

    assert report["summary"] == {
        "points_total": 1,
        "points_fetch_ok": 1,
        "points_basket_ok": 1,
        "points_signals_ok": 1,
        "points_historical_signals_ok": 1,
        "points_watchlist_alerts_ok": 1,
        "failed_points": [],
    }


def test_failed_point_is_recorded_instead_of_crashing() -> None:
    point = {"point_code": "p404", "name": "Missing", "district": "Nowhere"}
    result = updater.summarize_point_result(
        point,
        {"failed_requests": [{"error": "network"}]},
        {"ok": False, "errors": ["processed directory not found"]},
        {"ok": False, "errors": ["basket failed"]},
        {"ok": False, "errors": ["signals failed"]},
        {"ok": False, "errors": ["historical failed"]},
        {"ok": False, "errors": ["alerts failed"]},
    )
    report = updater.build_update_report(
        points=[result],
        date_value="2026-04-25",
        preset="demo_daily",
        max_points=1,
        sync_demo_data=False,
    )

    assert result["fetch_ok"] is False
    assert report["summary"]["failed_points"] == ["p404"]
    assert "basket failed" in result["errors"]
    assert "historical failed" in result["errors"]
    assert "alerts failed" in result["errors"]


def test_sync_demo_data_uses_temp_replace_and_keeps_source(tmp_path: Path) -> None:
    processed_root = tmp_path / "data" / "processed"
    source_point_dir = _write_fake_processed(processed_root)
    demo_root = tmp_path / "demo_data" / "processed"
    _write_jsonl(demo_root / "old-date" / "p999" / "supermarkets.jsonl", [{"old": True}])

    synced_date_dir = updater.sync_processed_to_demo_data(
        "2026-04-25",
        ["p001"],
        processed_root=processed_root,
        demo_processed_root=demo_root,
    )

    assert source_point_dir.exists()
    assert synced_date_dir == demo_root / "2026-04-25"
    assert (demo_root / "2026-04-25" / "p001" / "category_1_prices.jsonl").exists()
    assert not (demo_root / "old-date").exists()
    assert not (tmp_path / "demo_data" / "processed_tmp").exists()


def test_dry_run_collect_does_not_write_demo_data(tmp_path: Path) -> None:
    processed_root = tmp_path / "data" / "processed"
    _write_fake_processed(processed_root)
    demo_root = tmp_path / "demo_data" / "processed"
    demo_root.mkdir(parents=True)
    config_path = tmp_path / "points.json"
    config_path.write_text(
        json.dumps([{"point_code": "p001", "name": "Point 1", "district": "Macau"}]),
        encoding="utf-8",
    )

    report = updater.collect_update_results(
        updater.UpdateOptions(
            max_points=1,
            preset="demo_daily",
            run_date="2026-04-25",
            dry_run=True,
            sync_demo_data=True,
            processed_root=processed_root,
            demo_processed_root=demo_root,
            config_path=config_path,
        ),
        basket_builder=_fake_basket,
        signals_analyzer=_fake_signals,
        historical_signals_analyzer=_fake_historical_signals,
        watchlist_alert_generator=_fake_watchlist_alerts,
    )

    assert report["summary"]["failed_points"] == []
    assert report["sync_demo_data"] is False
    assert list(demo_root.iterdir()) == []
    assert report["points"][0]["historical_signals_ok"] is True
    assert report["points"][0]["historical_signals_count"] == 1
    assert report["points"][0]["historical_warnings"] == ["sample warning"]
    assert report["points"][0]["watchlist_alerts_ok"] is True
    assert report["points"][0]["watchlist_alerts_count"] == 1
    assert report["points"][0]["watchlist_alerts_notify_count"] == 1
    assert report["points"][0]["watchlist_alert_warnings"] == ["alert warning"]


def test_markdown_report_contains_point_table() -> None:
    report = updater.build_update_report(
        points=[
            {
                "point_code": "p001",
                "name": "Point 1",
                "district": "Macau",
                "supermarkets_found": 1,
                "products_found": 2,
                "price_records_found": 3,
                "fetch_ok": True,
                "validation_ok": True,
                "basket_ok": True,
                "signals_ok": True,
                "historical_signals_ok": True,
                "historical_signals_count": 2,
                "watchlist_alerts_ok": True,
                "watchlist_alerts_count": 3,
                "watchlist_alerts_notify_count": 2,
                "errors": [],
            }
        ],
        date_value="2026-04-25",
        preset="demo_daily",
        max_points=1,
        sync_demo_data=False,
    )

    markdown = updater.build_markdown_report(report)

    assert "| point_code | name | district | supermarkets | products | price_records | fetch_ok | validation_ok | basket_ok | signals_ok | historical_ok | historical_count | alerts_ok | alerts_count | notify_count | errors |" in markdown
    assert "| p001 | Point 1 | Macau | 1 | 2 | 3 | true | true | true | true | true | 2 | true | 3 | 2 |  |" in markdown


def test_historical_signal_smoke_treats_warnings_as_ok() -> None:
    result = updater.run_historical_signals_smoke(
        "2026-04-25",
        "p001",
        Path("unused"),
        historical_signals_analyzer=_fake_historical_signals,
    )

    assert result["ok"] is True
    assert result["signals_count"] == 1
    assert result["warnings"] == ["sample warning"]


def test_watchlist_alert_smoke_treats_warnings_as_ok() -> None:
    result = updater.run_watchlist_alerts_smoke(
        "2026-04-25",
        "p001",
        Path("unused"),
        {"product_oid": 10, "product_name": "Rice"},
        watchlist_alert_generator=_fake_watchlist_alerts,
    )

    assert result["ok"] is True
    assert result["alerts_count"] == 1
    assert result["notify_count"] == 1
    assert result["warnings"] == ["alert warning"]


def test_watchlist_alert_smoke_without_product_oid_is_non_fatal() -> None:
    result = updater.run_watchlist_alerts_smoke("2026-04-25", "p001", Path("unused"), None)

    assert result["ok"] is True
    assert result["alerts_count"] == 0
    assert result["warnings"]
