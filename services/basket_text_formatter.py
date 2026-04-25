from __future__ import annotations

from typing import Any


def _money(value: Any) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):.1f} MOP"


def _plan_by_type(plans: list[dict[str, Any]], plan_type: str | None) -> dict[str, Any] | None:
    for plan in plans:
        if plan.get("plan_type") == plan_type:
            return plan
    return None


def _first_available_plan(plans: list[dict[str, Any]]) -> dict[str, Any] | None:
    for plan in plans:
        if plan.get("estimated_total_mop") is not None:
            return plan
    return plans[0] if plans else None


def select_display_plan(result: dict[str, Any]) -> dict[str, Any] | None:
    plans = result.get("plans") or []
    recommended = _plan_by_type(plans, result.get("recommended_plan_type"))
    if recommended is not None:
        return recommended
    return _first_available_plan(plans)


def format_basket_text(
    result: dict[str, Any],
    original_text: str,
    point: dict[str, Any] | None = None,
) -> str:
    point = point or {}
    selected_plan = select_display_plan(result)
    stores = selected_plan.get("stores", []) if selected_plan else []
    items = selected_plan.get("items", []) if selected_plan else []

    lines = [
        "澳門採購決策建議",
        "",
        f"資料日期：{result.get('date')}",
        f"採集點 / 地區：{point.get('name') or result.get('point_code')} / {point.get('district') or 'N/A'}",
        f"原始輸入句子：{original_text}",
        "",
        "已解析購物清單：",
    ]

    parsed_items = result.get("parsed_items") or []
    if parsed_items:
        for item in parsed_items:
            lines.append(f"- {item.get('keyword')} x {item.get('quantity', 1)}")
    else:
        lines.append("- 無法解析商品")

    lines.extend(
        [
            "",
            f"推薦方案名稱：{(selected_plan or {}).get('plan_type') or result.get('recommended_plan_type')}",
            f"推薦原因：{result.get('recommendation_reason')}",
            "建議超市：",
        ]
    )

    if stores:
        for store in stores:
            lines.append(f"- {store.get('supermarket_name')} ({store.get('supermarket_oid')})")
    else:
        lines.append("- N/A")

    lines.extend(["", "每件商品："])
    if items:
        for item in items:
            lines.extend(
                [
                    f"- 商品名：{item.get('product_name')}",
                    f"  規格：{item.get('package_quantity')}",
                    f"  數量：{item.get('requested_quantity')}",
                    f"  單價：{_money(item.get('unit_price_mop'))}",
                    f"  小計：{_money(item.get('subtotal_mop'))}",
                    f"  超市名稱：{item.get('supermarket_name')}",
                ]
            )
    else:
        lines.append("- N/A")

    lines.extend(
        [
            "",
            f"預估總價：{_money((selected_plan or {}).get('estimated_total_mop'))}",
            "",
            "其他方案摘要：",
        ]
    )

    for plan in result.get("plans", []):
        lines.append(f"- {plan.get('plan_type')}: {_money(plan.get('estimated_total_mop'))}")

    lines.extend(["", "免責提示：價格只供參考，以店內標示為準。"])
    return "\n".join(lines)
