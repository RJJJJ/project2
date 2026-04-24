from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_PROCESSED_ROOT = PROJECT_ROOT / "data" / "processed"
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "collection_points.json"


def connect(database_url: str) -> Any:
    try:
        import psycopg

        return psycopg.connect(database_url)
    except ImportError:
        try:
            import psycopg2

            return psycopg2.connect(database_url)
        except ImportError as exc:
            raise RuntimeError("Install psycopg or psycopg2 to use PostgreSQL import.") from exc


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
            if isinstance(value, dict):
                rows.append(value)
    return rows


def load_collection_points(config_path: Path) -> dict[str, dict[str, Any]]:
    if not config_path.exists():
        return {}
    points = json.loads(config_path.read_text(encoding="utf-8"))
    return {str(point["point_code"]): point for point in points}


def latest_processed_date(processed_root: Path) -> str:
    candidates = [path.name for path in processed_root.iterdir() if path.is_dir()]
    if not candidates:
        raise FileNotFoundError(f"No processed date directories found in {processed_root}")
    return sorted(candidates)[-1]


def point_dirs(processed_root: Path, collection_date: str, point_code: str | None) -> list[Path]:
    date_dir = processed_root / collection_date
    if not date_dir.exists():
        raise FileNotFoundError(f"Processed date directory not found: {date_dir}")
    if point_code:
        path = date_dir / point_code
        if not path.exists():
            raise FileNotFoundError(f"Processed point directory not found: {path}")
        return [path]
    return sorted([path for path in date_dir.iterdir() if path.is_dir()])


def execute_schema(conn: Any) -> None:
    statements = [
        """
        CREATE TABLE IF NOT EXISTS collection_points (
            point_code TEXT PRIMARY KEY,
            name TEXT,
            district TEXT,
            lat DOUBLE PRECISION,
            lng DOUBLE PRECISION,
            dst INTEGER,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS categories (
            category_id INTEGER PRIMARY KEY,
            category_name TEXT,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS products (
            product_oid BIGINT PRIMARY KEY,
            product_name TEXT,
            quantity TEXT,
            category_id INTEGER REFERENCES categories(category_id),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS supermarkets (
            supermarket_oid BIGINT PRIMARY KEY,
            supermarket_id TEXT,
            supermarket_name TEXT,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS price_records (
            id BIGSERIAL PRIMARY KEY,
            product_oid BIGINT NOT NULL REFERENCES products(product_oid),
            supermarket_oid BIGINT NOT NULL REFERENCES supermarkets(supermarket_oid),
            point_code TEXT NOT NULL REFERENCES collection_points(point_code),
            collection_date DATE NOT NULL,
            category_id INTEGER REFERENCES categories(category_id),
            price_mop NUMERIC,
            discount TEXT,
            flag TEXT,
            source_url TEXT,
            raw_payload JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (product_oid, supermarket_oid, point_code, collection_date)
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_price_records_collection_date ON price_records(collection_date)",
        "CREATE INDEX IF NOT EXISTS idx_price_records_point_code ON price_records(point_code)",
        "CREATE INDEX IF NOT EXISTS idx_price_records_category_id ON price_records(category_id)",
    ]
    with conn.cursor() as cur:
        for statement in statements:
            cur.execute(statement)
    conn.commit()


def upsert_collection_point(conn: Any, point_code: str, point: dict[str, Any] | None) -> None:
    point = point or {"point_code": point_code}
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO collection_points (point_code, name, district, lat, lng, dst, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, now())
            ON CONFLICT (point_code) DO UPDATE SET
                name = EXCLUDED.name,
                district = EXCLUDED.district,
                lat = EXCLUDED.lat,
                lng = EXCLUDED.lng,
                dst = EXCLUDED.dst,
                updated_at = now()
            """,
            (
                point_code,
                point.get("name"),
                point.get("district"),
                point.get("lat"),
                point.get("lng"),
                point.get("dst"),
            ),
        )


def upsert_supermarkets(conn: Any, rows: list[dict[str, Any]]) -> int:
    count = 0
    with conn.cursor() as cur:
        for row in rows:
            supermarket_oid = row.get("supermarket_oid")
            if supermarket_oid is None:
                continue
            cur.execute(
                """
                INSERT INTO supermarkets (supermarket_oid, supermarket_id, supermarket_name, updated_at)
                VALUES (%s, %s, %s, now())
                ON CONFLICT (supermarket_oid) DO UPDATE SET
                    supermarket_id = EXCLUDED.supermarket_id,
                    supermarket_name = EXCLUDED.supermarket_name,
                    updated_at = now()
                """,
                (
                    supermarket_oid,
                    row.get("supermarket_id"),
                    row.get("supermarket_name"),
                ),
            )
            count += 1
    return count


def upsert_categories_and_products(conn: Any, rows: list[dict[str, Any]]) -> tuple[int, int]:
    category_ids: set[int] = set()
    product_oids: set[int] = set()
    with conn.cursor() as cur:
        for row in rows:
            category_id = row.get("category_id")
            if category_id is not None:
                cur.execute(
                    """
                    INSERT INTO categories (category_id, category_name, updated_at)
                    VALUES (%s, %s, now())
                    ON CONFLICT (category_id) DO UPDATE SET
                        category_name = COALESCE(EXCLUDED.category_name, categories.category_name),
                        updated_at = now()
                    """,
                    (category_id, row.get("category_name")),
                )
                category_ids.add(int(category_id))

            product_oid = row.get("product_oid")
            if product_oid is None:
                continue
            cur.execute(
                """
                INSERT INTO products (product_oid, product_name, quantity, category_id, updated_at)
                VALUES (%s, %s, %s, %s, now())
                ON CONFLICT (product_oid) DO UPDATE SET
                    product_name = EXCLUDED.product_name,
                    quantity = EXCLUDED.quantity,
                    category_id = EXCLUDED.category_id,
                    updated_at = now()
                """,
                (
                    product_oid,
                    row.get("product_name"),
                    row.get("quantity"),
                    category_id,
                ),
            )
            product_oids.add(int(product_oid))
    return len(category_ids), len(product_oids)


def ensure_supermarkets_from_price_rows(conn: Any, rows: list[dict[str, Any]]) -> int:
    seen: set[int] = set()
    with conn.cursor() as cur:
        for row in rows:
            supermarket_oid = row.get("supermarket_oid")
            if supermarket_oid is None:
                continue
            supermarket_oid = int(supermarket_oid)
            if supermarket_oid in seen:
                continue
            cur.execute(
                """
                INSERT INTO supermarkets (supermarket_oid, updated_at)
                VALUES (%s, now())
                ON CONFLICT (supermarket_oid) DO NOTHING
                """,
                (supermarket_oid,),
            )
            seen.add(supermarket_oid)
    return len(seen)


def upsert_price_records(
    conn: Any,
    rows: list[dict[str, Any]],
    collection_date: str,
) -> int:
    count = 0
    with conn.cursor() as cur:
        for row in rows:
            if row.get("product_oid") is None or row.get("supermarket_oid") is None:
                continue
            cur.execute(
                """
                INSERT INTO price_records (
                    product_oid,
                    supermarket_oid,
                    point_code,
                    collection_date,
                    category_id,
                    price_mop,
                    discount,
                    flag,
                    source_url,
                    raw_payload,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, now())
                ON CONFLICT (product_oid, supermarket_oid, point_code, collection_date)
                DO UPDATE SET
                    category_id = EXCLUDED.category_id,
                    price_mop = EXCLUDED.price_mop,
                    discount = EXCLUDED.discount,
                    flag = EXCLUDED.flag,
                    source_url = EXCLUDED.source_url,
                    raw_payload = EXCLUDED.raw_payload,
                    updated_at = now()
                """,
                (
                    row.get("product_oid"),
                    row.get("supermarket_oid"),
                    row.get("point_code"),
                    collection_date,
                    row.get("category_id"),
                    row.get("price_mop"),
                    row.get("discount"),
                    row.get("flag"),
                    row.get("source_url"),
                    json.dumps(row.get("raw_payload"), ensure_ascii=False),
                ),
            )
            count += 1
    return count


def import_point_dir(
    conn: Any,
    point_dir: Path,
    collection_date: str,
    configured_points: dict[str, dict[str, Any]],
) -> dict[str, int | str]:
    point_code = point_dir.name
    upsert_collection_point(conn, point_code, configured_points.get(point_code))

    supermarket_rows = read_jsonl(point_dir / "supermarkets.jsonl")
    supermarket_count = upsert_supermarkets(conn, supermarket_rows)

    price_rows: list[dict[str, Any]] = []
    for path in sorted(point_dir.glob("category_*_prices.jsonl")):
        price_rows.extend(read_jsonl(path))

    category_count, product_count = upsert_categories_and_products(conn, price_rows)
    ensure_supermarkets_from_price_rows(conn, price_rows)
    price_record_count = upsert_price_records(conn, price_rows, collection_date)

    conn.commit()
    return {
        "point_code": point_code,
        "supermarkets_upserted": supermarket_count,
        "categories_upserted": category_count,
        "products_upserted": product_count,
        "price_records_upserted": price_record_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Import processed Consumer Council JSONL files into PostgreSQL.")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--processed-root", default=str(DEFAULT_PROCESSED_ROOT))
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--date", help="Processed collection date. Defaults to latest directory under data/processed.")
    parser.add_argument("--point-code", help="Import only one point_code.")
    args = parser.parse_args()

    if not args.database_url:
        raise SystemExit("Missing PostgreSQL connection string. Set DATABASE_URL or pass --database-url.")

    processed_root = Path(args.processed_root)
    collection_date = args.date or latest_processed_date(processed_root)
    # Validate date early, so the unique key uses a real collection date.
    date.fromisoformat(collection_date)

    configured_points = load_collection_points(Path(args.config))
    dirs = point_dirs(processed_root, collection_date, args.point_code)

    summary: dict[str, Any] = {
        "collection_date": collection_date,
        "points_processed": 0,
        "supermarkets_upserted": 0,
        "categories_upserted": 0,
        "products_upserted": 0,
        "price_records_upserted": 0,
        "failed_points": [],
    }

    conn = connect(args.database_url)
    try:
        execute_schema(conn)
        for point_dir in dirs:
            try:
                result = import_point_dir(conn, point_dir, collection_date, configured_points)
                summary["points_processed"] += 1
                summary["supermarkets_upserted"] += result["supermarkets_upserted"]
                summary["categories_upserted"] += result["categories_upserted"]
                summary["products_upserted"] += result["products_upserted"]
                summary["price_records_upserted"] += result["price_records_upserted"]
            except Exception as exc:  # noqa: BLE001 - continue importing other points
                conn.rollback()
                summary["failed_points"].append({"point_code": point_dir.name, "error": repr(exc)})
    finally:
        conn.close()

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if summary["failed_points"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
