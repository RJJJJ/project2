from pathlib import Path

from services.product_oid_price_planner import plan_cheapest_by_product_candidates_two_stores
from services.sqlite_store import connect_db, init_db


def _make_db(path: Path, rows):
    with connect_db(path) as conn:
        init_db(conn)
        conn.executemany("INSERT INTO supermarkets(supermarket_oid, supermarket_name) VALUES (?, ?)", [("s1", "Store 1"), ("s2", "Store 2")])
        conn.executemany("INSERT INTO products(product_oid, product_name, package_quantity, category_id, category_name) VALUES (?, ?, ?, ?, ?)", [("a", "Item A", "1", 1, "cat"), ("b", "Item B", "1", 1, "cat")])
        conn.executemany("INSERT INTO price_records(date, point_code, supermarket_oid, product_oid, price_mop, category_id, source_file) VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
        conn.commit()


def _items():
    return [
        {"raw_item_name": "A", "intent_id": "a", "quantity": 1, "candidate_products": [{"product_oid": "a"}]},
        {"raw_item_name": "B", "intent_id": "b", "quantity": 1, "candidate_products": [{"product_oid": "b"}]},
    ]


def test_two_store_plan_can_beat_single_store(tmp_path: Path):
    db = tmp_path / "p.sqlite3"
    _make_db(db, [("2026-04-28", "p001", "s1", "a", 5, 1, "t"), ("2026-04-28", "p001", "s1", "b", 20, 1, "t"), ("2026-04-28", "p001", "s2", "a", 20, 1, "t"), ("2026-04-28", "p001", "s2", "b", 5, 1, "t")])
    result = plan_cheapest_by_product_candidates_two_stores(db, "p001", _items())
    assert result["status"] == "ok"
    assert result["best_plan"]["store_count"] == 2
    assert result["best_plan"]["estimated_total_mop"] == 10


def test_two_store_plan_uses_one_store_when_it_is_best(tmp_path: Path):
    db = tmp_path / "p.sqlite3"
    _make_db(db, [("2026-04-28", "p001", "s1", "a", 5, 1, "t"), ("2026-04-28", "p001", "s1", "b", 6, 1, "t"), ("2026-04-28", "p001", "s2", "a", 20, 1, "t"), ("2026-04-28", "p001", "s2", "b", 10, 1, "t")])
    result = plan_cheapest_by_product_candidates_two_stores(db, "p001", _items())
    assert result["best_plan"]["store_count"] == 1
    assert result["best_plan"]["supermarket_oids"] == ["s1"]
