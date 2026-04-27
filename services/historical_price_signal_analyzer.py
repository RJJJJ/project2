from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from services.processed_data_loader import DEFAULT_PROCESSED_ROOT, build_supermarket_lookup, load_price_records


NOT_ENOUGH_HISTORY_WARNING = "Not enough historical dates for historical comparison."

SIGNAL_PRIORITY = {
    "near_historical_low": 0,
    "below_average": 1,
    "unusual_high": 2,
}


def _parse_iso_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _available_dates(point_code: str, processed_root: Path) -> list[str]:
    if not processed_root.exists():
        return []
    dates: list[str] = []
    for date_dir in processed_root.iterdir():
        if not date_dir.is_dir() or _parse_iso_date(date_dir.name) is None:
            continue
        point_dir = date_dir / point_code
        if point_dir.is_dir() and any(point_dir.glob("category_*_prices.jsonl")):
            dates.append(date_dir.name)
    return sorted(dates)


def _resolve_current_date(point_code: str, current_date: str, processed_root: Path) -> tuple[str | None, list[str]]:
    dates = _available_dates(point_code, processed_root)
    if current_date == "latest":
        return (dates[-1] if dates else None), dates
    return current_date, dates


def _window_dates(dates: list[str], current_date: str, lookback_days: int) -> list[str]:
    current = _parse_iso_date(current_date)
    if current is None:
        return [current_date] if current_date in dates else []
    start = current - timedelta(days=max(lookback_days, 0))
    return [
        date_value
        for date_value in dates
        if (parsed := _parse_iso_date(date_value)) is not None and start <= parsed <= current
    ]


def _priced_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("product_oid") is not None and row.get("price_mop") is not None]


def _daily_minima(date_value: str, point_code: str, processed_root: Path) -> dict[Any, dict[str, Any]]:
    lookup = build_supermarket_lookup(date_value, point_code, processed_root)
    best_by_product: dict[Any, dict[str, Any]] = {}
    for row in _priced_rows(load_price_records(date_value, point_code, processed_root)):
        product_oid = row.get("product_oid")
        price = float(row["price_mop"])
        current_best = best_by_product.get(product_oid)
        if current_best is not None and price >= float(current_best["price_mop"]):
            continue
        output = dict(row)
        supermarket_oid = output.get("supermarket_oid")
        supermarket = lookup.get(int(supermarket_oid)) if supermarket_oid is not None else None
        output["supermarket_name"] = supermarket.get("supermarket_name") if supermarket else output.get("supermarket_name")
        output["price_mop"] = price
        best_by_product[product_oid] = output
    return best_by_product


def _current_availability(date_value: str, point_code: str, processed_root: Path) -> dict[Any, int]:
    stores_by_product: dict[Any, set[Any]] = defaultdict(set)
    for row in _priced_rows(load_price_records(date_value, point_code, processed_root)):
        product_oid = row.get("product_oid")
        supermarket_oid = row.get("supermarket_oid")
        if supermarket_oid is not None:
            stores_by_product[product_oid].add(supermarket_oid)
    return {product_oid: len(stores) for product_oid, stores in stores_by_product.items()}


def _confidence(date_count: int) -> str:
    if date_count >= 7:
        return "high"
    if date_count >= 4:
        return "medium"
    return "low"


def _round(value: float) -> float:
    return round(value, 2)


def analyze_historical_price_signals(
    point_code: str,
    current_date: str = "latest",
    lookback_days: int = 30,
    top_n: int = 10,
    processed_root: Path | None = None,
) -> dict[str, Any]:
    root = processed_root or DEFAULT_PROCESSED_ROOT
    selected_date, available_dates = _resolve_current_date(point_code, current_date, root)
    warnings: list[str] = []

    if not selected_date:
        return {
            "point_code": point_code,
            "current_date": current_date,
            "lookback_days": lookback_days,
            "signals": [],
            "summary": {
                "signals_count": 0,
                "near_historical_low_count": 0,
                "below_average_count": 0,
                "unusual_high_count": 0,
            },
            "warnings": [f"Processed data not found for point_code={point_code}."],
        }

    window_dates = _window_dates(available_dates, selected_date, lookback_days)
    if selected_date not in window_dates and (root / selected_date / point_code).exists():
        window_dates.append(selected_date)
        window_dates.sort()

    if len(window_dates) < 2:
        warnings.append(NOT_ENOUGH_HISTORY_WARNING)
        return {
            "point_code": point_code,
            "current_date": selected_date,
            "lookback_days": lookback_days,
            "signals": [],
            "summary": {
                "signals_count": 0,
                "near_historical_low_count": 0,
                "below_average_count": 0,
                "unusual_high_count": 0,
            },
            "warnings": warnings,
        }

    daily_by_date = {date_value: _daily_minima(date_value, point_code, root) for date_value in window_dates}
    current_minima = daily_by_date.get(selected_date, {})
    availability = _current_availability(selected_date, point_code, root)
    confidence = _confidence(len(window_dates))

    signals: list[dict[str, Any]] = []
    for product_oid, current_row in current_minima.items():
        price_points = [
            float(product_rows[product_oid]["price_mop"])
            for product_rows in daily_by_date.values()
            if product_oid in product_rows
        ]
        if len(price_points) < 2:
            continue

        current_price = float(current_row["price_mop"])
        historical_min = min(price_points)
        historical_avg = sum(price_points) / len(price_points)
        if historical_avg <= 0:
            continue

        discount_vs_avg = (historical_avg - current_price) / historical_avg * 100
        signal_type: str | None = None
        reason: str | None = None
        if current_price <= historical_min * 1.03:
            signal_type = "near_historical_low"
            reason = f"目前價格接近近{lookback_days}日最低價。"
        elif current_price <= historical_avg * 0.90:
            signal_type = "below_average"
            reason = f"目前價格低於近{lookback_days}日平均價 {abs(discount_vs_avg):.1f}%。"
        elif current_price >= historical_avg * 1.20:
            signal_type = "unusual_high"
            reason = f"目前價格高於近{lookback_days}日平均價 {abs(discount_vs_avg):.1f}%，建議暫緩購買或比價。"

        if signal_type is None:
            continue

        signals.append(
            {
                "signal_type": signal_type,
                "product_oid": product_oid,
                "product_name": current_row.get("product_name"),
                "package_quantity": current_row.get("package_quantity") or current_row.get("quantity"),
                "category_name": current_row.get("category_name"),
                "current_min_price_mop": _round(current_price),
                "historical_min_price_mop": _round(historical_min),
                "historical_avg_price_mop": _round(historical_avg),
                "discount_vs_avg_percent": _round(discount_vs_avg),
                "store_name": current_row.get("supermarket_name"),
                "store_count": availability.get(product_oid, 0),
                "confidence": confidence,
                "reason": reason,
            }
        )

    signals = sorted(
        signals,
        key=lambda item: (
            SIGNAL_PRIORITY.get(str(item.get("signal_type")), 99),
            -float(item.get("discount_vs_avg_percent") or 0),
            -int(item.get("store_count") or 0),
            str(item.get("product_name") or ""),
        ),
    )[: max(top_n, 0)]

    return {
        "point_code": point_code,
        "current_date": selected_date,
        "lookback_days": lookback_days,
        "signals": signals,
        "summary": {
            "signals_count": len(signals),
            "near_historical_low_count": sum(1 for item in signals if item.get("signal_type") == "near_historical_low"),
            "below_average_count": sum(1 for item in signals if item.get("signal_type") == "below_average"),
            "unusual_high_count": sum(1 for item in signals if item.get("signal_type") == "unusual_high"),
        },
        "warnings": warnings,
    }
