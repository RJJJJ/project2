from __future__ import annotations

import sqlite3
from pathlib import Path

from services.sqlite_store import connect_db, init_db, upsert_collection_points
from services.sqlite_query_service import (
    build_sqlite_simple_basket,
    get_cheapest_offer_for_keyword,
    get_latest_date,
    get_product_price_rows,
    list_collection_points,
    search_product_candidates_for_point,
    search_products,
)

RICE = "\u7c73"
SHAMPOO = "\u6d17\u982d\u6c34"
MISSING = "\u4e0d\u5b58\u5728"


def _seed_db(db_path: Path) -> sqlite3.Connection:
    conn = connect_db(db_path)
    init_db(conn)
    upsert_collection_points(
        conn,
        [
            {"point_code": "p001", "name": "\u9ad8\u58eb\u5fb7", "district": "\u6fb3\u9580\u534a\u5cf6", "lat": 22.1, "lng": 113.5, "dst": 500},
            {"point_code": "p002", "name": "\u53f0\u5c71", "district": "\u6fb3\u9580\u534a\u5cf6", "lat": 22.2, "lng": 113.6, "dst": 500},
        ],
    )
    conn.executemany(
        "INSERT INTO supermarkets(supermarket_oid, supermarket_name) VALUES (?, ?)",
        [("s1", "\u5e73\u50f9\u8d85\u5e02"), ("s2", "\u8857\u574a\u8d85\u5e02"), ("s3", "\u8cb4\u50f9\u8d85\u5e02")],
    )
    conn.executemany(
        "INSERT INTO products(product_oid, product_name, package_quantity, category_id, category_name) VALUES (?, ?, ?, ?, ?)",
        [
            ("rice-a", "\u73cd\u73e0\u7c73", "1\u516c\u65a4", 1, "\u7c73\u985e"),
            ("rice-b", "\u5bb6\u5ead\u88dd\u7c73", "5\u516c\u65a4", 1, "\u7c73\u985e"),
            ("shampoo-a", "\u6eab\u548c\u6d17\u982d\u6c34", "500\u6beb\u5347", 9, "\u500b\u4eba\u8b77\u7406"),
            ("tissue-a", "\u76d2\u88dd\u7d19\u5dfe", "5\u76d2", 10, "\u7d19\u54c1"),
        ],
    )
    conn.executemany(
        "INSERT INTO price_records(date, point_code, supermarket_oid, product_oid, price_mop, category_id, source_file) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            ("2026-04-27", "p001", "s1", "rice-a", 16.0, 1, "category_1_prices.jsonl"),
            ("2026-04-28", "p001", "s1", "rice-a", 15.0, 1, "category_1_prices.jsonl"),
            ("2026-04-28", "p001", "s2", "rice-a", 13.0, 1, "category_1_prices.jsonl"),
            ("2026-04-28", "p001", "s3", "rice-a", 17.0, 1, "category_1_prices.jsonl"),
            ("2026-04-28", "p001", "s1", "rice-b", 60.0, 1, "category_1_prices.jsonl"),
            ("2026-04-28", "p001", "s1", "shampoo-a", 35.0, 9, "category_9_prices.jsonl"),
            ("2026-04-28", "p001", "s1", "tissue-a", 20.0, 10, "category_10_prices.jsonl"),
        ],
    )
    conn.commit()
    return conn


def test_get_latest_date(tmp_path: Path) -> None:
    conn = _seed_db(tmp_path / "test.sqlite3")

    assert get_latest_date(conn) == "2026-04-28"


def test_list_collection_points(tmp_path: Path) -> None:
    conn = _seed_db(tmp_path / "test.sqlite3")

    points = list_collection_points(conn)

    assert [point["point_code"] for point in points] == ["p001", "p002"]


def test_search_products_keyword(tmp_path: Path) -> None:
    conn = _seed_db(tmp_path / "test.sqlite3")

    products = search_products(conn, RICE)

    assert [item["product_oid"] for item in products] == ["rice-a", "rice-b"]
    assert products[0]["package_quantity"] == "1\u516c\u65a4"


def test_get_product_price_rows_sorted_by_price(tmp_path: Path) -> None:
    conn = _seed_db(tmp_path / "test.sqlite3")

    rows = get_product_price_rows(conn, "2026-04-28", "p001", "rice-a")

    assert [row["price_mop"] for row in rows] == [13.0, 15.0, 17.0]
    assert rows[0]["supermarket_name"] == "\u8857\u574a\u8d85\u5e02"


def test_search_product_candidates_for_point_deterministic_sort(tmp_path: Path) -> None:
    conn = _seed_db(tmp_path / "test.sqlite3")

    candidates = search_product_candidates_for_point(conn, "2026-04-28", "p001", RICE)

    assert [item["product_oid"] for item in candidates] == ["rice-a", "rice-b"]
    assert candidates[0]["store_count"] == 3
    assert candidates[0]["is_recommended"] is True
    assert candidates[1]["is_recommended"] is False


def test_get_cheapest_offer_for_keyword(tmp_path: Path) -> None:
    conn = _seed_db(tmp_path / "test.sqlite3")

    offer = get_cheapest_offer_for_keyword(conn, "2026-04-28", "p001", RICE)

    assert offer is not None
    assert offer["product_oid"] == "rice-a"
    assert offer["unit_price_mop"] == 13.0
    assert offer["source"] == "sqlite"


def test_build_sqlite_simple_basket_total(tmp_path: Path) -> None:
    conn = _seed_db(tmp_path / "test.sqlite3")

    basket = build_sqlite_simple_basket(
        conn,
        "2026-04-28",
        "p001",
        [{"keyword": RICE, "quantity": 1}, {"keyword": SHAMPOO, "quantity": 2}, {"keyword": MISSING, "quantity": 1}],
    )

    assert basket["estimated_total_mop"] == 83.0
    assert basket["items"][0]["matched"] is True
    assert basket["items"][2]["matched"] is False
    assert f"No SQLite offer found for keyword: {MISSING}" in basket["warnings"]


def _seed_ranking_db(db_path: Path) -> sqlite3.Connection:
    conn = connect_db(db_path)
    init_db(conn)
    upsert_collection_points(conn, [{"point_code": "p001", "name": "\u9ad8\u58eb\u5fb7", "district": "\u6fb3\u9580\u534a\u5cf6", "lat": 22.1, "lng": 113.5, "dst": 500}])
    conn.executemany(
        "INSERT INTO supermarkets(supermarket_oid, supermarket_name) VALUES (?, ?)",
        [("s1", "A"), ("s2", "B")],
    )
    conn.executemany(
        "INSERT INTO products(product_oid, product_name, package_quantity, category_id, category_name) VALUES (?, ?, ?, ?, ?)",
        [
            ("rice-good-a", "\u5bcc\u58eb\u73cd\u73e0\u7c73", "5\u516c\u65a4", 1, "\u7c73\u985e"),
            ("rice-noodle", "\u5abd\u5abd\u5feb\u719f\u6e05\u6e6f\u7c73\u7c89", "55\u514b", 2, "\u7a40\u985e\u98df\u54c1"),
            ("corn", "\u751c\u7c9f\u7c73\u7c92", "340\u514b", 4, "\u7f50\u982d\u985e"),
            ("rice-good-b", "\u91d1\u8c61\u724c\u9802\u4e0a\u6cf0\u570b\u9999\u7c73", "8\u516c\u65a4", 1, "\u7c73\u985e"),
            ("tissue-box", "Tempo \u76d2\u88dd\u7d19\u5dfe", "5\u76d2", 10, "\u7d19\u54c1"),
            ("tissue-roll", "\u7dad\u9054\u5377\u7d19", "10\u5377", 10, "\u7d19\u54c1"),
            ("wet-wipes", "\u6ef4\u9732\u842c\u7528\u6d88\u6bd2\u6fd5\u7d19\u5dfe", "80\u7247", 10, "\u7d19\u54c1"),
            ("shampoo-en", "Head & Shoulders Shampoo", "750ml", 9, "\u500b\u4eba\u8b77\u7406"),
            ("shampoo-zh", "\u6f58\u5a77\u6d17\u9aee\u9732", "700ml", 9, "\u500b\u4eba\u8b77\u7406"),
            ("body-wash", "\u67d0\u54c1\u724c\u6c90\u6d74\u9732", "1L", 9, "\u500b\u4eba\u8b77\u7406"),
            ("tie-a", "\u5e73\u50f9\u7259\u818fA", "120\u514b", 9, "\u500b\u4eba\u8b77\u7406"),
            ("tie-b", "\u5e73\u50f9\u7259\u818fB", "120\u514b", 9, "\u500b\u4eba\u8b77\u7406"),
        ],
    )
    prices = [
        ("2026-04-28", "p001", "s1", "rice-good-a", 52.0, 1, "category_1_prices.jsonl"),
        ("2026-04-28", "p001", "s2", "rice-good-b", 76.0, 1, "category_1_prices.jsonl"),
        ("2026-04-28", "p001", "s1", "rice-noodle", 2.9, 2, "category_2_prices.jsonl"),
        ("2026-04-28", "p001", "s1", "corn", 7.0, 4, "category_4_prices.jsonl"),
        ("2026-04-28", "p001", "s1", "tissue-box", 28.0, 10, "category_10_prices.jsonl"),
        ("2026-04-28", "p001", "s1", "tissue-roll", 32.0, 10, "category_10_prices.jsonl"),
        ("2026-04-28", "p001", "s1", "wet-wipes", 18.0, 10, "category_10_prices.jsonl"),
        ("2026-04-28", "p001", "s1", "shampoo-en", 49.0, 9, "category_9_prices.jsonl"),
        ("2026-04-28", "p001", "s1", "shampoo-zh", 45.0, 9, "category_9_prices.jsonl"),
        ("2026-04-28", "p001", "s1", "body-wash", 22.0, 9, "category_9_prices.jsonl"),
        ("2026-04-28", "p001", "s1", "tie-b", 12.0, 9, "category_9_prices.jsonl"),
        ("2026-04-28", "p001", "s1", "tie-a", 12.0, 9, "category_9_prices.jsonl"),
    ]
    conn.executemany(
        "INSERT INTO price_records(date, point_code, supermarket_oid, product_oid, price_mop, category_id, source_file) VALUES (?, ?, ?, ?, ?, ?, ?)",
        prices,
    )
    conn.commit()
    return conn


def test_rice_ranking_avoids_rice_noodles_and_corn(tmp_path: Path) -> None:
    conn = _seed_ranking_db(tmp_path / "ranking.sqlite3")

    candidates = search_product_candidates_for_point(conn, "2026-04-28", "p001", RICE)

    assert candidates[0]["product_oid"] in {"rice-good-a", "rice-good-b"}
    assert candidates[0]["product_oid"] not in {"rice-noodle", "corn"}
    assert all(item["product_oid"] != "corn" for item in candidates[:2])


def test_tissue_ranking_avoids_disinfecting_wet_wipes_first(tmp_path: Path) -> None:
    conn = _seed_ranking_db(tmp_path / "ranking.sqlite3")

    candidates = search_product_candidates_for_point(conn, "2026-04-28", "p001", "\u7d19\u5dfe")

    assert candidates[0]["product_oid"] in {"tissue-box", "tissue-roll"}
    assert candidates[0]["product_oid"] != "wet-wipes"


def test_shampoo_expansion_recalls_shampoo_and_hair_wash(tmp_path: Path) -> None:
    conn = _seed_ranking_db(tmp_path / "ranking.sqlite3")

    candidates = search_product_candidates_for_point(conn, "2026-04-28", "p001", SHAMPOO)

    candidate_oids = [item["product_oid"] for item in candidates]
    assert "shampoo-en" in candidate_oids
    assert "shampoo-zh" in candidate_oids
    assert candidates[0]["product_oid"] in {"shampoo-en", "shampoo-zh"}
    assert candidates[0]["product_oid"] != "body-wash"


def test_sqlite_simple_basket_matches_core_items_after_expansion(tmp_path: Path) -> None:
    conn = _seed_ranking_db(tmp_path / "ranking.sqlite3")

    basket = build_sqlite_simple_basket(
        conn,
        "2026-04-28",
        "p001",
        [{"keyword": RICE, "quantity": 1}, {"keyword": "\u7d19\u5dfe", "quantity": 1}, {"keyword": SHAMPOO, "quantity": 1}],
    )

    assert [item["matched"] for item in basket["items"]] == [True, True, True]
    assert basket["warnings"] == []
    assert basket["items"][0]["product_oid"] in {"rice-good-a", "rice-good-b"}


def test_candidate_sorting_is_deterministic_for_ties(tmp_path: Path) -> None:
    conn = _seed_ranking_db(tmp_path / "ranking.sqlite3")

    candidates = search_product_candidates_for_point(conn, "2026-04-28", "p001", "\u7259\u818f")

    assert [item["product_oid"] for item in candidates[:2]] == ["tie-a", "tie-b"]
