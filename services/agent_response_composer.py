from __future__ import annotations

import json
import os
import time
from urllib import request

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
UNSUPPORTED_HELPFUL_MESSAGE = "\u6211\u53ef\u4ee5\u5e6b\u4f60\u6bd4\u8f03\u6fb3\u9580\u8d85\u5e02\u516c\u958b\u76e3\u6e2c\u5546\u54c1\u50f9\u683c\u3002\u8acb\u8f38\u5165\u8cfc\u7269\u6e05\u55ae\u3001\u54c1\u724c\u6216\u5546\u54c1\u540d\u7a31\uff0c\u4f8b\u5982\u300c\u7802\u7cd6\u540c\u6d17\u982d\u6c34\u300d\u3001\u300c\u51fa\u524d\u4e00\u4e01\u9ebb\u6cb9\u5473\u300d\u6216\u300cBB\u7528\u6fd5\u7d19\u5dfe\u300d\u3002"
SUBJECTIVE_HELPFUL_MESSAGE = "\u76ee\u524d\u6c92\u6709\u53e3\u5473\u8a55\u5206\u3001\u4eba\u6c23\u6216\u5065\u5eb7\u5206\u6578\u7b49\u4e3b\u89c0\u8cc7\u6599\u3002\u4f60\u53ef\u4ee5\u6539\u70ba\u8f38\u5165\u60f3\u6bd4\u8f03\u7684\u5546\u54c1\uff0c\u4f8b\u5982\u300c\u5373\u98df\u9eb5\uff0f\u85af\u7247\uff0f\u6731\u53e4\u529b\u98f2\u54c1\u300d\u3002"
BRAND_MSG = "\u7cfb\u7d71\u5df2\u628a\u9019\u6b21\u67e5\u8a62\u8996\u70ba\u54c1\u724c\u641c\u5c0b\uff0c\u76ee\u524d\u6c92\u6709\u6307\u5b9a\u53e3\u5473\uff0c\u6703\u5148\u6574\u7406\u8a72\u54c1\u724c\u4e0b\u8f03\u76f8\u95dc\u7684\u5019\u9078\u5546\u54c1\u3002"
DIRECT_MEDIUM_MSG = "\u7cfb\u7d71\u5df2\u8fa8\u8b58\u70ba\u8f03\u660e\u78ba\u7684\u5546\u54c1\u67e5\u8a62\uff0c\u6703\u512a\u5148\u6bd4\u5c0d\u6700\u76f8\u95dc\u5546\u54c1\u3002"
DIRECT_STRONG_MSG = "\u7cfb\u7d71\u5df2\u8fa8\u8b58\u70ba\u660e\u78ba\u5546\u54c1\u67e5\u8a62\uff0c\u6703\u76f4\u63a5\u6574\u7406\u6700\u76f8\u95dc\u7d50\u679c\u3002"
STATUS_OK_MSG = "\u5df2\u6839\u64da\u76ee\u524d\u516c\u958b\u50f9\u683c\u8cc7\u6599\u6574\u7406\u51fa\u53ef\u6bd4\u8f03\u65b9\u6848\u3002"
STATUS_CLARIFY_MSG = "\u90e8\u5206\u5546\u54c1\u4ecd\u9700\u8981\u4f60\u78ba\u8a8d\u985e\u578b\uff0c\u50f9\u683c\u7d50\u679c\u53ea\u6703\u5305\u542b\u5df2\u78ba\u8a8d\u5546\u54c1\u3002"
STATUS_PARTIAL_MSG = "\u90e8\u5206\u5546\u54c1\u5df2\u6210\u529f\u6bd4\u5c0d\uff0c\u5176\u9918\u672a\u6536\u9304\u6216\u4ecd\u9700\u78ba\u8a8d\uff0c\u4ee5\u4e0b\u5148\u986f\u793a\u53ef\u8a08\u50f9\u90e8\u5206\u3002"
STATUS_NOT_COVERED_MSG = "\u9019\u6b21\u67e5\u8a62\u7684\u5546\u54c1\u66ab\u672a\u6536\u9304\u65bc\u76ee\u524d\u516c\u958b\u76e3\u6e2c\u8cc7\u6599\u3002"
STATUS_ERROR_MSG = "\u66ab\u6642\u672a\u80fd\u5b8c\u6210\u67e5\u50f9\uff0c\u8acb\u7a0d\u5f8c\u518d\u8a66\u3002"
RESOLVED_PREFIX = "\u5df2\u78ba\u8a8d\u5546\u54c1\uff1a"
AMBIGUOUS_PREFIX = "\u9700\u8981\u6f84\u6e05\uff1a"
NOT_COVERED_PREFIX = "\u66ab\u672a\u6536\u9304\uff1a"
NOT_COVERED_SUFFIX = "\u300c\u672a\u6536\u9304\u300d\u4ee3\u8868\u76ee\u524d\u516c\u958b\u76e3\u6e2c\u8cc7\u6599\u672a\u6db5\u84cb\uff0c\u4e0d\u4ee3\u8868\u8d85\u5e02\u4e00\u5b9a\u6c92\u6709\u552e\u8ce3\u3002"
BEST_PLAN_LABEL = "\u6700\u4f73\u65b9\u6848"
TEMP_PLAN_LABEL = "\u5df2\u78ba\u8a8d\u5546\u54c1\u66ab\u6642\u8a08\u50f9"


def compose_agent_response_template(agent_result: dict) -> str:
    status = str(agent_result.get("status") or "error")
    router = agent_result.get("query_router") or {}
    query_type = str(agent_result.get("query_type") or router.get("query_type") or "")
    resolved_items = list(agent_result.get("resolved_items") or [])
    ambiguous_items = list(agent_result.get("ambiguous_items") or [])
    not_covered_items = list(agent_result.get("not_covered_items") or [])
    price_plan = agent_result.get("price_plan") or {}
    decision_result = price_plan.get("decision_result") or {}
    best_plan = decision_result.get("best_recommendation") or price_plan.get("best_plan") or {}

    if query_type == "subjective_recommendation":
        return SUBJECTIVE_HELPFUL_MESSAGE
    if status == "unsupported" or query_type == "unsupported_request":
        return UNSUPPORTED_HELPFUL_MESSAGE

    parts: list[str] = []
    if query_type == "brand_search":
        parts.append(BRAND_MSG)
    elif query_type in {"direct_product_search", "partial_product_search"}:
        if any((summary.get("direct_search") or {}).get("confidence") == "medium" for summary in agent_result.get("candidate_summary") or []):
            parts.append(DIRECT_MEDIUM_MSG)
        else:
            parts.append(DIRECT_STRONG_MSG)

    if status == "ok":
        parts.append(STATUS_OK_MSG)
    elif status == "needs_clarification":
        parts.append(STATUS_CLARIFY_MSG)
    elif status == "partial":
        parts.append(STATUS_PARTIAL_MSG)
    elif status == "not_covered":
        parts.append(STATUS_NOT_COVERED_MSG)
    else:
        parts.append(STATUS_ERROR_MSG)

    if resolved_items:
        labels = "\u3001".join(str(item.get("raw_item_name") or "") for item in resolved_items if item.get("raw_item_name"))
        if labels:
            parts.append(f"{RESOLVED_PREFIX}{labels}\u3002")
    if ambiguous_items:
        labels = "\u3001".join(str(item.get("raw_item_name") or "") for item in ambiguous_items if item.get("raw_item_name"))
        if labels:
            parts.append(f"{AMBIGUOUS_PREFIX}{labels}\u3002")
    if not_covered_items:
        labels = "\u3001".join(str(item.get("raw_item_name") or "") for item in not_covered_items if item.get("raw_item_name"))
        if labels:
            parts.append(f"{NOT_COVERED_PREFIX}{labels}\u3002")
            parts.append(NOT_COVERED_SUFFIX)
    if best_plan:
        store_name = str(best_plan.get("supermarket_name") or "").strip()
        total = best_plan.get("estimated_total_mop")
        if total is not None:
            label = BEST_PLAN_LABEL if status == "ok" else TEMP_PLAN_LABEL
            store_text = f"\uff1a{store_name}" if store_name else ""
            parts.append(f"{label}{store_text}\uff0c\u4f30\u8a08\u7e3d\u50f9 MOP {float(total):.2f}\u3002")
    return "".join(parts)


def compose_agent_response_with_gemini(
    agent_result: dict,
    api_key: str | None = None,
    model: str | None = None,
    timeout_seconds: int = 20,
) -> tuple[str, dict]:
    started = time.time()
    diagnostics = {
        "composer_mode": "gemini",
        "composer_provider": "gemini",
        "composer_model": None,
        "composer_used": "gemini",
        "composer_errors": [],
        "composer_fallback_reason": None,
        "composer_latency_ms": None,
    }
    selected_key = api_key or os.getenv("GEMINI_API_KEY")
    selected_model = model or os.getenv("PROJECT2_GEMINI_MODEL") or DEFAULT_GEMINI_MODEL
    diagnostics["composer_model"] = selected_model
    if not selected_key:
        diagnostics["composer_used"] = "template_fallback"
        diagnostics["composer_fallback_reason"] = "Missing GEMINI_API_KEY"
        diagnostics["composer_errors"].append("Missing GEMINI_API_KEY")
        diagnostics["composer_latency_ms"] = round((time.time() - started) * 1000, 2)
        return compose_agent_response_template(agent_result), diagnostics

    prompt = (
        "You are Project2 final response composer. "
        "Use only the provided structured agent_result. "
        "Do not invent products, prices, or stores. "
        "If status is unsupported, return a short shopping-guidance message.\n\n"
        + json.dumps(agent_result, ensure_ascii=False)
    )
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{selected_model}:generateContent?key={selected_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.2}}
    req = request.Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with request.urlopen(req, timeout=max(1, int(timeout_seconds))) as response:
            body = response.read().decode("utf-8")
        data = json.loads(body)
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        if not text:
            raise ValueError("Gemini returned empty text")
        diagnostics["composer_latency_ms"] = round((time.time() - started) * 1000, 2)
        return text, diagnostics
    except Exception as exc:
        diagnostics["composer_used"] = "template_fallback"
        diagnostics["composer_fallback_reason"] = str(exc)
        diagnostics["composer_errors"].append(str(exc))
        diagnostics["composer_latency_ms"] = round((time.time() - started) * 1000, 2)
        return compose_agent_response_template(agent_result), diagnostics


def compose_agent_response(agent_result: dict, composer_mode: str = "template") -> tuple[str, dict]:
    if composer_mode == "gemini":
        return compose_agent_response_with_gemini(agent_result)
    diagnostics = {"composer_mode": "template", "composer_used": "template", "composer_errors": []}
    return compose_agent_response_template(agent_result), diagnostics
