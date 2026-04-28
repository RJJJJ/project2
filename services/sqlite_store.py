from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "app_state" / "project2_dev.sqlite3"


def connect_db(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS collection_points (
            point_code TEXT PRIMARY KEY,
            name TEXT,
            district TEXT,
            lat REAL,
            lng REAL,
            dst INTEGER
        );

        CREATE TABLE IF NOT EXISTS supermarkets (
            supermarket_oid TEXT PRIMARY KEY,
            supermarket_name TEXT,
            address TEXT,
            lat REAL,
            lng REAL
        );

        CREATE TABLE IF NOT EXISTS products (
            product_oid TEXT PRIMARY KEY,
            product_name TEXT,
            package_quantity TEXT,
            category_id INTEGER,
            category_name TEXT
        );

        CREATE TABLE IF NOT EXISTS price_records (
            date TEXT,
            point_code TEXT,
            supermarket_oid TEXT,
            product_oid TEXT,
            price_mop REAL,
            category_id INTEGER,
            source_file TEXT,
            PRIMARY KEY(date, point_code, supermarket_oid, product_oid, category_id)
        );
        """
    )
    conn.commit()


def upsert_collection_points(conn: sqlite3.Connection, points: Iterable[dict[str, Any]]) -> int:
    rows = [
        (
            str(point.get("point_code", "")),
            point.get("name"),
            point.get("district"),
            point.get("lat"),
            point.get("lng"),
            point.get("dst"),
        )
        for point in points
        if point.get("point_code")
    ]
    conn.executemany(
        """
        INSERT INTO collection_points(point_code, name, district, lat, lng, dst)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(point_code) DO UPDATE SET
            name=excluded.name,
            district=excluded.district,
            lat=excluded.lat,
            lng=excluded.lng,
            dst=excluded.dst
        """,
        rows,
    )
    conn.commit()
    return len(rows)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _as_text(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _supermarket_oid(row: dict[str, Any]) -> str | None:
    return _as_text(row.get("supermarket_oid") or row.get("supermarket_id") or row.get("supermarket_code"))


def _product_oid(row: dict[str, Any]) -> str | None:
    return _as_text(row.get("product_oid") or row.get("item_oid") or row.get("oid"))


def _price(row: dict[str, Any]) -> float | None:
    return _as_float(row.get("price_mop") or row.get("price"))


def import_processed_date(
    conn: sqlite3.Connection,
    date: str,
    point_codes: list[str],
    processed_root: Path,
    collection_points: list[dict[str, Any]],
) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []
    imported_points = 0
    product_ids: set[str] = set()
    supermarket_ids: set[str] = set()
    price_keys: set[tuple[str, str, str, str, int]] = set()

    upsert_collection_points(conn, collection_points)

    for point_code in point_codes:
        point_dir = processed_root / date / point_code
        if not point_dir.exists():
            warnings.append(f"missing point directory: {point_code}")
            continue
        imported_points += 1

        for row in _read_jsonl(point_dir / "supermarkets.jsonl"):
            supermarket_oid = _supermarket_oid(row)
            if not supermarket_oid:
                warnings.append(f"missing supermarket oid in {point_code}/supermarkets.jsonl")
                continue
            raw = row.get("raw_payload") if isinstance(row.get("raw_payload"), dict) else {}
            name = row.get("supermarket_name") or raw.get("name") or raw.get("name_cn")
            conn.execute(
                """
                INSERT INTO supermarkets(supermarket_oid, supermarket_name, address, lat, lng)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(supermarket_oid) DO UPDATE SET
                    supermarket_name=excluded.supermarket_name,
                    address=excluded.address,
                    lat=excluded.lat,
                    lng=excluded.lng
                """,
                (
                    supermarket_oid,
                    name,
                    row.get("address") or raw.get("address") or raw.get("address_cn"),
                    _as_float(row.get("lat") or raw.get("lat")),
                    _as_float(row.get("lng") or raw.get("lng")),
                ),
            )
            supermarket_ids.add(supermarket_oid)

        for price_file in sorted(point_dir.glob("category_*_prices.jsonl")):
            for row in _read_jsonl(price_file):
                product_oid = _product_oid(row)
                supermarket_oid = _supermarket_oid(row)
                category_id = _as_int(row.get("category_id"))
                price_mop = _price(row)
                if not product_oid or not supermarket_oid or category_id is None or price_mop is None:
                    warnings.append(f"skipped unrecognized row in {point_code}/{price_file.name}")
                    continue
                conn.execute(
                    """
                    INSERT INTO products(product_oid, product_name, package_quantity, category_id, category_name)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(product_oid) DO UPDATE SET
                        product_name=excluded.product_name,
                        package_quantity=excluded.package_quantity,
                        category_id=excluded.category_id,
                        category_name=excluded.category_name
                    """,
                    (
                        product_oid,
                        row.get("product_name") or row.get("name"),
                        row.get("package_quantity") or row.get("quantity"),
                        category_id,
                        row.get("category_name"),
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO price_records(date, point_code, supermarket_oid, product_oid, price_mop, category_id, source_file)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(date, point_code, supermarket_oid, product_oid, category_id) DO UPDATE SET
                        price_mop=excluded.price_mop,
                        source_file=excluded.source_file
                    """,
                    (date, point_code, supermarket_oid, product_oid, price_mop, category_id, price_file.name),
                )
                product_ids.add(product_oid)
                price_keys.add((date, point_code, supermarket_oid, product_oid, category_id))
    conn.commit()
    return {
        "points_imported": imported_points,
        "products_upserted": len(product_ids),
        "supermarkets_upserted": len(supermarket_ids),
        "price_records_upserted": len(price_keys),
        "warnings": warnings,
        "errors": errors,
    }
