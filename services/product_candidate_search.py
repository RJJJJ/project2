from __future__ import annotations

from pathlib import Path
from typing import Any

from services.processed_data_loader import build_supermarket_lookup, load_price_records
from services.product_aliases import expand_keyword


def _row_match(row: dict[str, Any], aliases: list[str]) -> str | None:
    fields = (row.get("product_name"), row.get("category_name"))
    for alias in aliases:
        normalized = alias.strip().casefold()
        if not normalized:
            continue
        if any(normalized in str(value).casefold() for value in fields if value is not None):
            return alias
    return None


def _exactish_score(keyword: str, matched_alias: str | None, product_name: Any) -> int:
    name = str(product_name or "").casefold()
    values = [keyword, matched_alias or ""]
    return 1 if any(value.strip().casefold() in name for value in values if value and value.strip()) else 0


def search_product_candidates(
    date: str,
    point_code: str,
    keyword: str,
    limit: int = 10,
    processed_root: Path | None = None,
) -> list[dict[str, Any]]:
    """Search priced product candidates for a keyword at one processed point.

    v0 intentionally uses the existing alias file and processed JSONL files only. It
    does not change the lower-level price query behavior used by the optimizer.
    """
    aliases = expand_keyword(keyword)
    supermarkets = build_supermarket_lookup(date, point_code, processed_root)
    grouped: dict[Any, dict[str, Any]] = {}

    for row in load_price_records(date, point_code, processed_root):
        if row.get("price_mop") is None:
            continue
        matched_alias = _row_match(row, aliases)
        if matched_alias is None:
            continue
        product_oid = row.get("product_oid")
        if product_oid is None:
            continue

        price = float(row["price_mop"])
        supermarket_oid = row.get("supermarket_oid")
        supermarket = None
        if supermarket_oid is not None:
            supermarket = supermarkets.get(int(supermarket_oid))
        supermarket_name = (
            supermarket.get("supermarket_name")
            if supermarket
            else row.get("supermarket_name")
        )

        candidate = grouped.setdefault(
            product_oid,
            {
                "keyword": keyword,
                "matched_alias": matched_alias,
                "product_oid": product_oid,
                "product_name": row.get("product_name"),
                "package_quantity": row.get("quantity"),
                "category_name": row.get("category_name"),
                "min_price_mop": price,
                "max_price_mop": price,
                "_store_oids": set(),
                "_sample_supermarkets": [],
                "_exactish": _exactish_score(keyword, matched_alias, row.get("product_name")),
            },
        )
        candidate["min_price_mop"] = min(float(candidate["min_price_mop"]), price)
        candidate["max_price_mop"] = max(float(candidate["max_price_mop"]), price)
        candidate["_exactish"] = max(
            int(candidate["_exactish"]),
            _exactish_score(keyword, matched_alias, row.get("product_name")),
        )
        if supermarket_oid is not None:
            candidate["_store_oids"].add(supermarket_oid)
        if supermarket_name and supermarket_name not in candidate["_sample_supermarkets"]:
            candidate["_sample_supermarkets"].append(supermarket_name)

    candidates: list[dict[str, Any]] = []
    for candidate in grouped.values():
        store_count = len(candidate["_store_oids"])
        score = int(candidate["_exactish"]) * 1000 + store_count
        candidates.append(
            {
                "keyword": candidate["keyword"],
                "matched_alias": candidate["matched_alias"],
                "product_oid": candidate["product_oid"],
                "product_name": candidate["product_name"],
                "package_quantity": candidate["package_quantity"],
                "category_name": candidate["category_name"],
                "min_price_mop": candidate["min_price_mop"],
                "max_price_mop": candidate["max_price_mop"],
                "store_count": store_count,
                "sample_supermarkets": candidate["_sample_supermarkets"][:3],
                "score": score,
            }
        )

    candidates.sort(
        key=lambda item: (
            -int(item["score"] >= 1000),
            -int(item["store_count"]),
            float(item["min_price_mop"]),
            str(item.get("product_name") or ""),
        )
    )
    return candidates[: max(0, int(limit))]
