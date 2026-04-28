from __future__ import annotations

import json
from pathlib import Path

from scripts.query_sqlite_store import main
from services.sqlite_store import connect_db, init_db, upsert_collection_points

RICE = "\u7c73"
SHAMPOO = "\u6d17\u982d\u6c34"


def _seed_db(db_path: Path) -> None:
    with connect_db(db_path) as conn:
        init_db(conn)
        upsert_collection_points(conn, [{"point_code": "p001", "name": "\u9ad8\u58eb\u5fb7", "district": "\u6fb3\u9580\u534a\u5cf6", "lat": 22.1, "lng": 113.5, "dst": 500}])
        conn.execute("INSERT INTO supermarkets(supermarket_oid, supermarket_name) VALUES (?, ?)", ("s1", "\u5e73\u50f9\u8d85\u5e02"))
        conn.executemany(
            "INSERT INTO products(product_oid, product_name, package_quantity, category_id, category_name) VALUES (?, ?, ?, ?, ?)",
            [("rice-a", "\u73cd\u73e0\u7c73", "1\u516c\u65a4", 1, "\u7c73\u985e"), ("shampoo-a", "\u6eab\u548c\u6d17\u982d\u6c34", "500\u6beb\u5347", 9, "\u500b\u4eba\u8b77\u7406")],
        )
        conn.executemany(
            "INSERT INTO price_records(date, point_code, supermarket_oid, product_oid, price_mop, category_id, source_file) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [("2026-04-28", "p001", "s1", "rice-a", 13.0, 1, "category_1_prices.jsonl"), ("2026-04-28", "p001", "s1", "shampoo-a", 35.0, 9, "category_9_prices.jsonl")],
        )
        conn.commit()


def _json_from_stdout(capsys):  # noqa: ANN001
    return json.loads(capsys.readouterr().out)


def test_cli_health_mode(tmp_path: Path, capsys) -> None:  # noqa: ANN001
    db_path = tmp_path / "test.sqlite3"
    _seed_db(db_path)

    exit_code = main(["--db-path", str(db_path), "--mode", "health"])
    payload = _json_from_stdout(capsys)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["latest_date"] == "2026-04-28"
    assert payload["products_count"] == 2


def test_cli_basket_mode(tmp_path: Path, capsys) -> None:  # noqa: ANN001
    db_path = tmp_path / "test.sqlite3"
    _seed_db(db_path)

    exit_code = main(["--db-path", str(db_path), "--mode", "basket", "--point-code", "p001", "--keyword", RICE, "--keyword", SHAMPOO])
    payload = _json_from_stdout(capsys)

    assert exit_code == 0
    assert payload["estimated_total_mop"] == 48.0
    assert [item["matched"] for item in payload["items"]] == [True, True]


def test_cli_missing_db_returns_json_error(tmp_path: Path, capsys) -> None:  # noqa: ANN001
    db_path = tmp_path / "missing.sqlite3"

    exit_code = main(["--db-path", str(db_path), "--mode", "health"])
    payload = _json_from_stdout(capsys)

    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["errors"] == [f"SQLite DB not found: {db_path}"]
