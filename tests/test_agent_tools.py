from __future__ import annotations

import json
from pathlib import Path

from scripts.run_agent_tool_demo import main as demo_main
from services.agent_tools import tool_build_basket, tool_format_answer, tool_search_product_candidates
from services.sqlite_store import connect_db, init_db, upsert_collection_points

RICE = "\u7c73"
TEXT = "\u6211\u5728\u9ad8\u58eb\u5fb7\uff0c\u60f3\u8cb7\u4e00\u5305\u7c73\u3001\u4e00\u5305\u7d19\u5dfe"


def _seed_db(db_path: Path) -> None:
    with connect_db(db_path) as conn:
        init_db(conn)
        upsert_collection_points(conn, [{"point_code": "p001", "name": "\u9ad8\u58eb\u5fb7", "district": "\u6fb3\u9580\u534a\u5cf6", "lat": 22.1, "lng": 113.5, "dst": 500}])
        conn.execute("INSERT INTO supermarkets(supermarket_oid, supermarket_name) VALUES (?, ?)", ("s1", "Store A"))
        conn.executemany(
            "INSERT INTO products(product_oid, product_name, package_quantity, category_id, category_name) VALUES (?, ?, ?, ?, ?)",
            [("rice", "\u5bcc\u58eb\u73cd\u73e0\u7c73", "5\u516c\u65a4", 1, "\u7c73\u985e"), ("tissue", "Tempo \u76d2\u88dd\u7d19\u5dfe", "5\u76d2", 15, "\u885b\u751f\u7d19")],
        )
        conn.executemany(
            "INSERT INTO price_records(date, point_code, supermarket_oid, product_oid, price_mop, category_id, source_file) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [("2026-04-28", "p001", "s1", "rice", 50.0, 1, "category_1_prices.jsonl"), ("2026-04-28", "p001", "s1", "tissue", 20.0, 15, "category_15_prices.jsonl")],
        )
        conn.commit()


def test_agent_tool_search_candidates_sqlite(tmp_path: Path) -> None:
    db_path = tmp_path / "test.sqlite3"
    _seed_db(db_path)

    result = tool_search_product_candidates({"provider": "sqlite", "db_path": db_path, "date": "latest", "point_code": "p001", "keyword": RICE})

    assert result["ok"] is True
    assert result["candidates"][0]["product_oid"] == "rice"


def test_agent_tool_build_basket_sqlite(tmp_path: Path) -> None:
    db_path = tmp_path / "test.sqlite3"
    _seed_db(db_path)

    result = tool_build_basket({"provider": "sqlite", "db_path": db_path, "date": "latest", "point_code": "p001", "items": [{"keyword": RICE, "quantity": 1}]})

    assert result["ok"] is True
    assert result["basket_result"]["estimated_total_mop"] == 50.0


def test_agent_tool_format_answer() -> None:
    result = tool_format_answer({"basket_result": {"date": "2026-04-28", "point_code": "p001", "items": [], "estimated_total_mop": 0.0, "warnings": []}})

    assert result["ok"] is True
    assert "answer_text" in result["answer"]


def test_run_agent_tool_demo_core_flow(tmp_path: Path, capsys) -> None:  # noqa: ANN001
    db_path = tmp_path / "test.sqlite3"
    _seed_db(db_path)

    exit_code = demo_main(["--text", TEXT, "--provider", "sqlite", "--point-code", "p001", "--db-path", str(db_path)])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["tool_calls"] == [{"tool": "tool_build_basket", "ok": True}, {"tool": "tool_format_answer", "ok": True}]
    assert payload["answer"]["facts_used"]["estimated_total_mop"] == 70.0
