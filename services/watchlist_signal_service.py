from __future__ import annotations

from pathlib import Path
from typing import Any

from services.historical_price_signal_analyzer import (
    NOT_ENOUGH_HISTORY_WARNING,
    _daily_minima,
    _resolve_current_date,
    _round,
    _window_dates,
)
from services.processed_data_loader import DEFAULT_PROCESSED_ROOT


def _normalize_product_oid(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _signal_from_prices(current_price: float, historical_min: float, historical_avg: float, lookback_days: int) -> tuple[str | None, str | None]:
    if historical_avg <= 0:
        return None, None

    discount_vs_avg = (historical_avg - current_price) / historical_avg * 100
    if current_price <= historical_min * 1.03:
        return "near_historical_low", f"目前價格接近近{lookback_days}日最低價。"
    if current_price <= historical_avg * 0.90:
        return "below_average", f"目前價格低於近{lookback_days}日平均價 {abs(discount_vs_avg):.1f}%。"
    if current_price >= historical_avg * 1.20:
        return "unusual_high", f"目前價格高於近{lookback_days}日平均價 {abs(discount_vs_avg):.1f}%，建議暫緩購買或比價。"
    return None, None


def _empty_item(input_item: dict[str, Any], warning: str) -> dict[str, Any]:
    return {
        "product_oid": input_item.get("product_oid"),
        "product_name": input_item.get("product_name"),
        "current_min_price_mop": None,
        "current_store_name": None,
        "historical_min_price_mop": None,
        "historical_avg_price_mop": None,
        "signal_type": None,
        "reason": None,
        "warnings": [warning],
    }


def analyze_watchlist_items(
    point_code: str,
    items: list[dict[str, Any]],
    date: str = "latest",
    lookback_days: int = 30,
    processed_root: Path | None = None,
) -> dict[str, Any]:
    root = processed_root or DEFAULT_PROCESSED_ROOT
    selected_date, available_dates = _resolve_current_date(point_code, date, root)
    response_warnings: list[str] = []

    if not items:
        return {
            "point_code": point_code,
            "date": selected_date or date,
            "items": [],
            "warnings": [],
        }

    if selected_date is None:
        warning = f"Processed data not found for point_code={point_code}."
        return {
            "point_code": point_code,
            "date": date,
            "items": [_empty_item(item, warning) for item in items],
            "warnings": [warning],
        }

    window_dates = _window_dates(available_dates, selected_date, lookback_days)
    if selected_date not in window_dates and (root / selected_date / point_code).exists():
        window_dates.append(selected_date)
        window_dates.sort()

    if len(window_dates) < 2:
        response_warnings.append(NOT_ENOUGH_HISTORY_WARNING)

    daily_by_date = {date_value: _daily_minima(date_value, point_code, root) for date_value in window_dates}
    if selected_date not in daily_by_date:
        daily_by_date[selected_date] = _daily_minima(selected_date, point_code, root)
    current_minima = daily_by_date.get(selected_date, {})

    output_items: list[dict[str, Any]] = []
    for input_item in items:
        product_oid = _normalize_product_oid(input_item.get("product_oid"))
        if product_oid is None:
            output_items.append(_empty_item(input_item, "Invalid product_oid."))
            continue

        current_row = current_minima.get(product_oid)
        if current_row is None:
            output_items.append(_empty_item(input_item, "今日無價格資料。"))
            continue

        item_warnings: list[str] = []
        price_points = [
            float(product_rows[product_oid]["price_mop"])
            for product_rows in daily_by_date.values()
            if product_oid in product_rows
        ]
        current_price = float(current_row["price_mop"])
        historical_min = min(price_points) if price_points else current_price
        historical_avg = sum(price_points) / len(price_points) if price_points else current_price

        signal_type: str | None = None
        reason: str | None = None
        if len(price_points) < 2:
            item_warnings.append(NOT_ENOUGH_HISTORY_WARNING)
        else:
            signal_type, reason = _signal_from_prices(current_price, historical_min, historical_avg, lookback_days)

        output_items.append(
            {
                "product_oid": product_oid,
                "product_name": current_row.get("product_name") or input_item.get("product_name"),
                "current_min_price_mop": _round(current_price),
                "current_store_name": current_row.get("supermarket_name"),
                "historical_min_price_mop": _round(historical_min),
                "historical_avg_price_mop": _round(historical_avg),
                "signal_type": signal_type,
                "reason": reason,
                "warnings": item_warnings,
            }
        )

    return {
        "point_code": point_code,
        "date": selected_date,
        "items": output_items,
        "warnings": response_warnings,
    }
