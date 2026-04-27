from __future__ import annotations

from pathlib import Path
from typing import Any

from services.watchlist_signal_service import analyze_watchlist_items


ALERT_TITLES = {
    "near_historical_low": "接近歷史低價",
    "below_average": "低於近期均價",
    "unusual_high": "異常偏高",
}


def _discount_vs_avg_percent(item: dict[str, Any]) -> float | None:
    current = item.get("current_min_price_mop")
    average = item.get("historical_avg_price_mop")
    if current is None or average in (None, 0):
        return None
    return round((float(average) - float(current)) / float(average) * 100, 2)


def _format_price(value: Any) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):.1f}"


def _build_alert(item: dict[str, Any], lookback_days: int) -> dict[str, Any] | None:
    if item.get("current_min_price_mop") is None:
        return None
    if item.get("warnings"):
        return None

    signal_type = item.get("signal_type")
    if signal_type not in ALERT_TITLES:
        return None

    discount = _discount_vs_avg_percent(item)
    product_name = item.get("product_name") or str(item.get("product_oid"))
    price = _format_price(item.get("current_min_price_mop"))

    severity = "medium"
    should_notify = True
    if signal_type == "below_average":
        if discount is None or discount < 10:
            return None
        severity = "high" if discount >= 20 else "medium"
        message = f"{product_name} 目前比近{lookback_days}日平均價低約 {discount:.1f}% 。"
    elif signal_type == "near_historical_low":
        message = f"{product_name} 目前最低價 {price} MOP，接近近{lookback_days}日最低價。"
    elif signal_type == "unusual_high":
        severity = "low"
        should_notify = False
        message = f"{product_name} 目前價格高於近期平均，建議暫緩購買或再比價。"
    else:
        return None

    return {
        "product_oid": item.get("product_oid"),
        "product_name": product_name,
        "alert_type": signal_type,
        "severity": severity,
        "title": ALERT_TITLES[signal_type],
        "message": message,
        "current_min_price_mop": item.get("current_min_price_mop"),
        "current_store_name": item.get("current_store_name"),
        "historical_min_price_mop": item.get("historical_min_price_mop"),
        "historical_avg_price_mop": item.get("historical_avg_price_mop"),
        "discount_vs_avg_percent": discount,
        "should_notify": should_notify,
        "warnings": list(item.get("warnings") or []),
    }


def generate_watchlist_alerts(
    point_code: str,
    items: list[dict[str, Any]],
    date: str = "latest",
    lookback_days: int = 30,
    processed_root: Path | None = None,
) -> dict[str, Any]:
    signals = analyze_watchlist_items(
        point_code=point_code,
        items=items,
        date=date,
        lookback_days=lookback_days,
        processed_root=processed_root,
    )

    alerts = [
        alert
        for item in signals.get("items", [])
        if (alert := _build_alert(item, lookback_days)) is not None
    ]

    return {
        "point_code": signals.get("point_code", point_code),
        "date": signals.get("date", date),
        "alerts": alerts,
        "summary": {
            "items_count": len(items),
            "alerts_count": len(alerts),
            "notify_count": sum(1 for alert in alerts if alert.get("should_notify")),
            "high_count": sum(1 for alert in alerts if alert.get("severity") == "high"),
            "medium_count": sum(1 for alert in alerts if alert.get("severity") == "medium"),
            "low_count": sum(1 for alert in alerts if alert.get("severity") == "low"),
        },
        "warnings": list(signals.get("warnings") or []),
        "item_warnings": [
            {
                "product_oid": item.get("product_oid"),
                "product_name": item.get("product_name"),
                "warnings": item.get("warnings"),
            }
            for item in signals.get("items", [])
            if item.get("warnings")
        ],
    }
