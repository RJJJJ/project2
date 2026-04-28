from __future__ import annotations

from typing import Any

DISCLAIMER = "\u6ce8\u610f\uff1a\u9019\u662f\u6839\u64da\u76ee\u524d\u8cc7\u6599\u5eab\u6700\u4f4e\u50f9\u751f\u6210\u7684 prototype \u5efa\u8b70\uff0c\u5be6\u969b\u5e97\u5167\u50f9\u683c\u53ef\u80fd\u6709\u8b8a\u3002"


def _items_from_basket(basket_result: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(basket_result.get("items"), list):
        return basket_result["items"]
    plans = basket_result.get("plans") if isinstance(basket_result.get("plans"), list) else []
    if plans and isinstance(plans[0], dict):
        return plans[0].get("items") or []
    return []


def _total_from_basket(basket_result: dict[str, Any]) -> float | None:
    if basket_result.get("estimated_total_mop") is not None:
        return float(basket_result["estimated_total_mop"])
    plans = basket_result.get("plans") if isinstance(basket_result.get("plans"), list) else []
    if plans and isinstance(plans[0], dict) and plans[0].get("estimated_total_mop") is not None:
        return float(plans[0]["estimated_total_mop"])
    return None


def format_grounded_basket_answer(basket_result: dict[str, Any], *, style: str = "simple") -> dict[str, Any]:
    items = _items_from_basket(basket_result)
    total = _total_from_basket(basket_result)
    matched = [item for item in items if item.get("matched", True)]
    unmatched = [item for item in items if item.get("matched") is False]
    stores = []
    for item in matched:
        store_name = item.get("supermarket_name")
        if store_name and store_name not in stores:
            stores.append(store_name)

    lines = ["\u63a8\u85a6\u4f60\u53ef\u4ee5\u9019\u6a23\u8cb7\uff1a", ""]
    if total is not None:
        lines.append(f"\u9810\u8a08\u7e3d\u50f9\uff1a{total:.1f} MOP")
        lines.append("")
    for index, item in enumerate(matched, start=1):
        keyword = item.get("keyword") or item.get("product_name") or f"item-{index}"
        product = item.get("product_name") or "\u672a\u77e5\u5546\u54c1"
        package = item.get("package_quantity") or ""
        price = item.get("unit_price_mop", item.get("price_mop"))
        store = item.get("supermarket_name") or "\u672a\u77e5\u8d85\u5e02"
        lines.append(f"{index}. {keyword}\uff1a{product} {package}".rstrip())
        if price is not None:
            lines.append(f"   - \u50f9\u683c\uff1a{float(price):.1f} MOP")
        lines.append(f"   - \u8d85\u5e02\uff1a{store}")
        lines.append("")
    if unmatched:
        lines.append("\u672a\u80fd\u627e\u5230\u7684\u5546\u54c1\uff1a")
        for item in unmatched:
            lines.append(f"- {item.get('keyword')}")
        lines.append("")
    lines.append(DISCLAIMER)
    facts = {
        "date": basket_result.get("date"),
        "point_code": basket_result.get("point_code"),
        "estimated_total_mop": total,
        "stores": stores,
        "items": items,
    }
    return {"answer_text": "\n".join(lines), "facts_used": facts, "warnings": basket_result.get("warnings", [])}
