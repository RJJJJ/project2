from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from services.brand_mining import build_brand_alias_index
from services.product_catalog_loader import load_products_from_sqlite
from services.sqlite_store import DEFAULT_DB_PATH


def main() -> int:
    parser = argparse.ArgumentParser(description="Export catalog-derived brand alias index.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--output-path", default="data/analysis/brand_alias_index.json")
    args = parser.parse_args()
    products = load_products_from_sqlite(args.db_path)
    index = build_brand_alias_index(products)
    output = Path(args.output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(index, ensure_ascii=False, indent=2, default=list), encoding="utf-8")
    print(f"brands: {len(index.get('brands') or [])}")
    print(f"aliases: {len(index.get('aliases') or {})}")
    print(f"output: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
