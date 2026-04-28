from __future__ import annotations

from pathlib import Path

from services.product_oid_price_planner import plan_cheapest_by_product_candidates
from services.sqlite_store import connect_db, init_db


def _make_db(path: Path) -> None:
    with connect_db(path) as conn:
        init_db(conn)
        conn.executemany(
            "INSERT INTO supermarkets(supermarket_oid, supermarket_name) VALUES (?, ?)",
            [("s1", "Store 1"), ("s2", "Store 2")],
        )
        conn.executemany(
            "INSERT INTO products(product_oid, product_name, package_quantity, category_id, category_name) VALUES (?, ?, ?, ?, ?)",
            [
                ("p_sugar", "太古純正砂糖", "400克", 5, "調味品"),
                ("p_shampoo", "多芬洗髮乳", "680毫升", 10, "個人護理用品"),
                ("p_chips", "樂事薯片", "80克", 11, "零食"),
            ],
        )
        conn.executemany(
            "INSERT INTO price_records(date, point_code, supermarket_oid, product_oid, price_mop, category_id, source_file) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                ("2026-04-28", "p001", "s1", "p_sugar", 10.0, 5, "test"),
                ("2026-04-28", "p001", "s1", "p_shampoo", 30.0, 10, "test"),
                ("2026-04-28", "p001", "s2", "p_sugar", 8.0, 5, "test"),
                ("2026-04-28", "p001", "s2", "p_chips", 12.0, 11, "test"),
            ],
        )
        conn.commit()


def _item(name: str, intent_id: str, oid: str, quantity: int = 1) -> dict:
    return {
        "raw_item_name": name,
        "intent_id": intent_id,
        "quantity": quantity,
        "candidate_products": [{"product_oid": oid, "product_name": name}],
    }


def test_complete_single_store_plan_and_quantity(tmp_path: Path):
    db_path = tmp_path / "prices.sqlite3"
    _make_db(db_path)
    result = plan_cheapest_by_product_candidates(
        db_path,
        "p001",
        [_item("砂糖", "cooking_sugar", "p_sugar", quantity=2), _item("洗頭水", "shampoo", "p_shampoo")],
    )
    assert result["status"] == "ok"
    assert result["best_plan"]["supermarket_oid"] == "s1"
    assert result["best_plan"]["estimated_total_mop"] == 50.0
    assert len(result["store_plans"]) == 1


def test_store_missing_item_is_not_complete_best_plan(tmp_path: Path):
    db_path = tmp_path / "prices.sqlite3"
    _make_db(db_path)
    result = plan_cheapest_by_product_candidates(
        db_path,
        "p001",
        [_item("洗頭水", "shampoo", "p_shampoo"), _item("薯片", "chips", "p_chips")],
    )
    assert result["status"] == "not_priceable"
    assert result["best_plan"] is None
    assert result["store_plans"] == []
    assert result["warnings"]
