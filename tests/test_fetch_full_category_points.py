from __future__ import annotations

import json
from pathlib import Path

from scripts.fetch_full_category_points import run_fetch_full_category_points


def _config(tmp_path: Path, count: int = 2) -> Path:
    points = [
        {"point_code": f"p{idx:03d}", "name": f"Point {idx}", "district": "????", "lat": 22.1, "lng": 113.5, "dst": 500}
        for idx in range(1, count + 1)
    ]
    path = tmp_path / "collection_points.json"
    path.write_text(json.dumps(points, ensure_ascii=False), encoding="utf-8")
    return path


def test_dry_run_does_not_call_fetcher(tmp_path: Path) -> None:
    called = False

    def fetcher(*args, **kwargs):  # noqa: ANN002, ANN003
        nonlocal called
        called = True
        raise AssertionError("fetcher should not be called")

    report = run_fetch_full_category_points(
        max_points=2,
        categories=[1, 19],
        run_date="2026-04-28",
        config_path=_config(tmp_path),
        dry_run=True,
        fetcher=fetcher,
    )

    assert called is False
    assert report["dry_run"] is True
    assert report["points_total"] == 2
    assert report["points_ok"] == 2


def test_single_point_failure_does_not_block_others(tmp_path: Path) -> None:
    def fetcher(point, categories, run_date, client):  # noqa: ANN001
        if point["point_code"] == "p001":
            raise RuntimeError("boom")
        return {"categories_processed": len(categories), "supermarkets_found": 1, "products_found": 2, "price_records_found": 3, "failed_requests": []}

    report = run_fetch_full_category_points(
        max_points=2,
        categories=[1, 19],
        run_date="2026-04-28",
        config_path=_config(tmp_path),
        dry_run=False,
        fetcher=fetcher,
        client=object(),
    )

    assert report["points_total"] == 2
    assert report["points_ok"] == 1
    assert report["failed_points"] == ["p001"]
    assert report["points"][1]["ok"] is True


def test_failed_points_non_empty_for_failed_requests(tmp_path: Path) -> None:
    def fetcher(point, categories, run_date, client):  # noqa: ANN001
        return {"categories_processed": 1, "supermarkets_found": 0, "products_found": 0, "price_records_found": 0, "failed_requests": [{"error": "bad"}]}

    report = run_fetch_full_category_points(
        max_points=1,
        categories=[1, 19],
        run_date="2026-04-28",
        config_path=_config(tmp_path, 1),
        fetcher=fetcher,
        client=object(),
    )

    assert report["failed_points"] == ["p001"]
    assert report["points_ok"] == 0


def test_all_success_points_ok(tmp_path: Path) -> None:
    def fetcher(point, categories, run_date, client):  # noqa: ANN001
        return {"categories_processed": len(categories), "supermarkets_found": 1, "products_found": 2, "price_records_found": 3, "failed_requests": []}

    report = run_fetch_full_category_points(
        max_points=2,
        categories=list(range(1, 20)),
        run_date="2026-04-28",
        config_path=_config(tmp_path),
        fetcher=fetcher,
        client=object(),
    )

    assert report["failed_points"] == []
    assert report["points_ok"] == 2
    assert report["points"][0]["categories_processed"] == 19
