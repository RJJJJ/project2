from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from scripts.import_processed_to_sqlite import run_import_processed_to_sqlite
from services.sqlite_store import connect_db, init_db


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def _config(tmp_path: Path, codes: list[str] | None = None) -> Path:
    codes = codes or ["p001"]
    points = [
        {"point_code": code, "name": f"Point {code}", "district": "????", "lat": 22.1, "lng": 113.5, "dst": 500}
        for code in codes
    ]
    path = tmp_path / "collection_points.json"
    path.write_text(json.dumps(points, ensure_ascii=False), encoding="utf-8")
    return path


def _sample_processed(processed: Path, date: str = "2026-04-28", point_code: str = "p001") -> None:
    point_dir = processed / date / point_code
    _write_jsonl(point_dir / "supermarkets.jsonl", [{"supermarket_oid": 175, "supermarket_name": "??? ?????"}])
    _write_jsonl(
        point_dir / "category_1_prices.jsonl",
        [
            {
                "point_code": point_code,
                "product_oid": 1,
                "product_name": "??????",
                "quantity": "5??",
                "category_id": 1,
                "category_name": "??",
                "supermarket_oid": 175,
                "price_mop": 55.9,
            },
            {
                "point_code": point_code,
                "product_oid": 2,
                "product_name": "???",
                "quantity": "1??",
                "category_id": 1,
                "category_name": "??",
                "supermarket_oid": 175,
                "price_mop": 13.5,
            },
        ],
    )


def _count(db_path: Path, table: str) -> int:
    with sqlite3.connect(db_path) as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_tables_created(tmp_path: Path) -> None:
    db_path = tmp_path / "test.sqlite3"
    with connect_db(db_path) as conn:
        init_db(conn)
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    assert {"collection_points", "supermarkets", "products", "price_records"}.issubset(tables)


def test_sample_processed_files_can_be_imported(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    db_path = tmp_path / "test.sqlite3"
    _sample_processed(processed)

    summary = run_import_processed_to_sqlite(
        date="2026-04-28",
        max_points=1,
        processed_root=processed,
        config_path=_config(tmp_path),
        db_path=db_path,
    )

    assert summary["errors"] == []
    assert summary["points_imported"] == 1
    assert _count(db_path, "collection_points") == 1
    assert _count(db_path, "supermarkets") == 1
    assert _count(db_path, "products") == 2
    assert _count(db_path, "price_records") == 2


def test_rerun_twice_does_not_duplicate_price_records(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    db_path = tmp_path / "test.sqlite3"
    _sample_processed(processed)
    kwargs = {"date": "2026-04-28", "max_points": 1, "processed_root": processed, "config_path": _config(tmp_path), "db_path": db_path}

    run_import_processed_to_sqlite(**kwargs)
    run_import_processed_to_sqlite(**kwargs)

    assert _count(db_path, "price_records") == 2


def test_missing_point_dir_warns_without_crash(tmp_path: Path) -> None:
    db_path = tmp_path / "test.sqlite3"
    processed = tmp_path / "processed"
    (processed / "2026-04-28").mkdir(parents=True)

    summary = run_import_processed_to_sqlite(
        date="2026-04-28",
        max_points=1,
        processed_root=processed,
        config_path=_config(tmp_path),
        db_path=db_path,
    )

    assert summary["errors"] == []
    assert summary["points_imported"] == 0
    assert "missing point directory: p001" in summary["warnings"]
