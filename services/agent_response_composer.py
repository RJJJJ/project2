from __future__ import annotations

import json
import os
from urllib import request

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


def compose_agent_response_template(agent_result: dict) -> str:
    status = str(agent_result.get("status") or "error")
    router = agent_result.get("query_router") or {}
    query_type = str(router.get("query_type") or "")
    resolved_items = list(agent_result.get("resolved_items") or [])
    ambiguous_items = list(agent_result.get("ambiguous_items") or [])
    not_covered_items = list(agent_result.get("not_covered_items") or [])
    price_plan = agent_result.get("price_plan") or {}
    decision_result = price_plan.get("decision_result") or {}
    best_plan = (decision_result.get("best_recommendation") or price_plan.get("best_plan") or {})

    parts: list[str] = []
    if query_type == "subjective_recommendation":
        return "我目前主要使用消委會公開價格資料，沒有口味、健康程度或用戶評分資料，因此不能可靠判斷「最好吃」或「最健康」。我可以幫你改為：查最便宜、列出收錄款式，或按品牌 / 類別比較價格。"
    if query_type == "unsupported_request":
        return "目前資料主要是公開價格資料，未包含銷量、庫存、即日特價、健康程度或用戶評分，因此不能可靠回答這類問題。我可以改為幫你查公開價格、列出收錄款式或比較同類商品。"
    if query_type == "brand_search":
        parts.append("你沒有指定口味或規格。我先按目前公開資料中收錄的「品牌」商品比較價格。")
    elif query_type in {"direct_product_search", "partial_product_search"}:
        if any((summary.get("direct_search") or {}).get("confidence") == "medium" for summary in agent_result.get("candidate_summary") or []):
            parts.append("我找到幾個相近商品，請確認是否是你想找的。")
        else:
            parts.append("已按你輸入的商品名稱查價。")

    if status == "ok":
        parts.append("\u5df2\u6839\u64da\u76ee\u524d\u516c\u958b\u76e3\u6e2c\u50f9\u683c\uff0c\u751f\u6210\u53ef\u6bd4\u8f03\u65b9\u6848\u3002")
    elif status == "needs_clarification":
        parts.append("\u90e8\u5206\u5546\u54c1\u9700\u8981\u4f60\u78ba\u8a8d\u985e\u578b\u3002\u4ee5\u4e0b\u50f9\u683c\u53ea\u5305\u542b\u5df2\u78ba\u8a8d\u5546\u54c1\u3002")
    elif status == "partial":
        parts.append("\u90e8\u5206\u5546\u54c1\u5df2\u53ef\u8a08\u50f9\uff0c\u90e8\u5206\u5546\u54c1\u66ab\u672a\u6536\u9304\u6216\u9700\u8981\u78ba\u8a8d\u3002")
    elif status == "not_covered":
        parts.append("\u76ee\u524d\u8f38\u5165\u7684\u5546\u54c1\u672a\u80fd\u5728\u516c\u958b\u76e3\u6e2c\u8cc7\u6599\u4e2d\u627e\u5230\u53ef\u6bd4\u8f03\u50f9\u683c\u3002")
    elif status == "unsupported":
        parts.append("目前資料不支持這類判斷。")
    else:
        parts.append("\u5206\u6790\u6642\u767c\u751f\u932f\u8aa4\uff0c\u8acb\u7a0d\u5f8c\u518d\u8a66\u3002")

    if resolved_items:
        labels = "\u3001".join(str(item.get("raw_item_name") or "") for item in resolved_items if item.get("raw_item_name"))
        if labels:
            parts.append(f"\u5df2\u7406\u89e3\u7684\u5546\u54c1\u5305\u62ec\uff1a{labels}\u3002")
    if ambiguous_items:
        labels = "\u3001".join(str(item.get("raw_item_name") or "") for item in ambiguous_items if item.get("raw_item_name"))
        if labels:
            parts.append(f"\u4ecd\u9700\u8981\u78ba\u8a8d\uff1a{labels}\u3002")
    if not_covered_items:
        labels = "\u3001".join(str(item.get("raw_item_name") or "") for item in not_covered_items if item.get("raw_item_name"))
        if labels:
            parts.append(f"\u66ab\u672a\u6536\u9304\uff1a{labels}\u3002")
            parts.append("\u9019\u4e0d\u4ee3\u8868\u8d85\u5e02\u6c92\u6709\u552e\u8ce3\uff0c\u53ea\u4ee3\u8868\u76ee\u524d\u7f3a\u5c11\u53ef\u9760\u516c\u958b\u50f9\u683c\u8cc7\u6599\u3002")
    if best_plan:
        store_name = str(best_plan.get("supermarket_name") or "").strip()
        total = best_plan.get("estimated_total_mop")
        if total is not None:
            label = "\u6700\u4fbf\u5b9c\u65b9\u6848" if status == "ok" else "\u5df2\u78ba\u8a8d\u5546\u54c1\u7684\u66ab\u6642\u8a08\u50f9"
            store_text = f"{store_name}\uff0c" if store_name else ""
            parts.append(f"{label}\uff1a{store_text}\u4f30\u7b97\u7e3d\u50f9 MOP {float(total):.2f}\u3002")
    return "".join(parts)


def compose_agent_response_with_gemini(
    agent_result: dict,
    api_key: str | None = None,
    model: str | None = None,
    timeout_seconds: int = 20,
) -> tuple[str, dict]:
    diagnostics = {"composer_mode": "gemini", "composer_used": "gemini", "composer_errors": []}
    selected_key = api_key or os.getenv("GEMINI_API_KEY")
    selected_model = model or os.getenv("PROJECT2_GEMINI_MODEL") or DEFAULT_GEMINI_MODEL
    if not selected_key:
        diagnostics["composer_used"] = "template_fallback"
        diagnostics["composer_errors"].append("Missing GEMINI_API_KEY")
        return compose_agent_response_template(agent_result), diagnostics

    prompt = (
        "\u4f60\u662f Project2 \u7684\u6700\u7d42\u56de\u8986 composer\u3002"
        "\u4f60\u53ea\u80fd\u6839\u64da\u63d0\u4f9b\u7684 structured agent_result \u751f\u6210\u7528\u6236\u53ef\u8b80\u4e2d\u6587\u3002"
        "\u4f60\u4e0d\u53ef\u65b0\u589e\u5546\u54c1\u3001\u4e0d\u53ef\u4fee\u6539\u50f9\u683c\u3001\u4e0d\u53ef\u6539\u5beb\u672a\u6536\u9304\u5546\u54c1\u70ba\u5176\u4ed6\u5546\u54c1\u3002"
        "\u5982\u679c status \u662f needs_clarification\uff0c\u5fc5\u9808\u660e\u78ba\u8aaa\u660e\u50f9\u683c\u53ea\u5305\u542b\u5df2\u78ba\u8a8d\u5546\u54c1\u3002"
        "\u5982\u679c\u5546\u54c1\u66ab\u672a\u6536\u9304\uff0c\u53ea\u80fd\u8aaa\u76ee\u524d\u6c92\u6709\u516c\u958b\u53ef\u6bd4\u8f03\u50f9\u683c\uff0c\u4e0d\u80fd\u8aaa\u5546\u54c1\u4e0d\u5b58\u5728\u3002"
        "\u4e0d\u8981\u8f38\u51fa JSON\uff0c\u4e0d\u8981\u4f7f\u7528 markdown code block\u3002\n\n"
        + json.dumps(agent_result, ensure_ascii=False)
    )
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{selected_model}:generateContent?key={selected_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.2}}
    req = request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=max(1, int(timeout_seconds))) as response:
            body = response.read().decode("utf-8")
        data = json.loads(body)
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        if not text:
            raise ValueError("Gemini returned empty text")
        return text, diagnostics
    except Exception as exc:  # pragma: no cover
        diagnostics["composer_used"] = "template_fallback"
        diagnostics["composer_errors"].append(str(exc))
        return compose_agent_response_template(agent_result), diagnostics


def compose_agent_response(agent_result: dict, composer_mode: str = "template") -> tuple[str, dict]:
    if composer_mode == "gemini":
        return compose_agent_response_with_gemini(agent_result)
    diagnostics = {"composer_mode": "template", "composer_used": "template", "composer_errors": []}
    return compose_agent_response_template(agent_result), diagnostics
