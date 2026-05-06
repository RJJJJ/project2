from __future__ import annotations

import json
import os
import time
from typing import Any
from urllib import request

from services.product_direct_search import normalize_product_name_for_lookup
from services.query_intent_router import QUERY_TYPES


CONFIDENCES = {"high", "medium", "low"}
GOALS = {"cheapest", "list_options", "specific_price", "subjective", "unknown"}
HARD_NOT_COVERED = {"??", "??", "M&M", "m&m"}
HIGH_RISK_SHORT = {"?", "?", "?", "?", "?", "??", "??", "?"}
ROUTER_SCHEMA_KEYS = {
    "query",
    "query_type",
    "confidence",
    "items",
    "needs_clarification",
    "clarification_options",
    "unsupported_reason",
    "reasons",
    "warnings",
}
DEFAULT_LLM_ROUTER_TIMEOUT_SECONDS = 8


def _base_diagnostics(provider: str, model: str | None) -> dict[str, Any]:
    return {
        "llm_router_provider": provider,
        "llm_router_model": model,
        "llm_router_used": "fallback",
        "llm_router_errors": [],
        "llm_router_latency_ms": None,
        "llm_router_raw_output": None,
        "router_merge_strategy": None,
        "router_merge_decision": None,
    }


def _extract_json_object(text: str) -> dict[str, Any]:
    payload = str(text or "").strip()
    if payload.startswith("```"):
        payload = payload.strip("`")
        if payload.lower().startswith("json"):
            payload = payload[4:].strip()
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        start = payload.find("{")
        end = payload.rfind("}")
        if start >= 0 and end > start:
            return json.loads(payload[start : end + 1])
        raise


def build_llm_router_prompt(query: str, planner_output: dict | None = None) -> str:
    examples = [
        ("????", "brand_search", "????", "unknown"),
        ("???????", "partial_product_search", "????", "unknown"),
        ("??????", "direct_product_search", None, "unknown"),
        ("??", "not_covered_request", None, "unknown"),
        ("?????", "subjective_recommendation", None, "subjective"),
        ("?????????", "basket_optimization", None, "unknown"),
        ("?", "ambiguous_request", None, "unknown"),
        ("BB?????", "category_search", None, "unknown"),
    ]
    few_shots = "\n".join(
        json.dumps(
            {
                "query": q,
                "query_type": qt,
                "confidence": "high",
                "items": [
                    {
                        "raw": q,
                        "quantity": 1,
                        "unit": None,
                        "query_type": qt,
                        "brand": brand,
                        "category_hint": "wet_wipe" if "???" in q else None,
                        "product_clues": [],
                        "goal": goal,
                        "confidence": "high",
                        "needs_clarification": qt == "ambiguous_request",
                        "clarification_options": [],
                    }
                ],
                "needs_clarification": qt == "ambiguous_request",
                "clarification_options": [],
                "unsupported_reason": "subjective data unavailable" if qt == "subjective_recommendation" else None,
                "reasons": ["few-shot example"],
                "warnings": [],
            },
            ensure_ascii=False,
        )
        for q, qt, brand, goal in examples
    )
    planner_json = json.dumps(planner_output or {}, ensure_ascii=False)
    return (
        "You are Project2 Query Intent Router. Return STRICT JSON only, no markdown and no prose.\n"
        "Schema keys: query, query_type, confidence, items, needs_clarification, clarification_options, unsupported_reason, reasons, warnings.\n"
        "Allowed query_type: basket_optimization, direct_product_search, partial_product_search, brand_search, category_search, subjective_recommendation, ambiguous_request, not_covered_request, unsupported_request, unknown.\n"
        "Allowed confidence: high, medium, low. Allowed goal: cheapest, list_options, specific_price, subjective, unknown.\n"
        "Rules: do not calculate prices; do not output product_oid; do not claim database availability; do not decide final product match; preserve raw user item words.\n"
        "Subjective queries such as ??/?? => subjective_recommendation or unsupported_request.\n"
        "Brand only such as ???? => brand_search. Brand + flavor such as ??????? => partial_product_search.\n"
        "Exact-looking product names such as ?????? => direct_product_search.\n"
        "Short ambiguous terms ?/?/?/?/?? => ambiguous_request. Known not-covered fresh items ?? => not_covered_request.\n"
        "If uncertain, use confidence low and query_type unknown or ambiguous_request.\n"
        "Few-shot outputs:\n"
        f"{few_shots}\n"
        f"Planner output context: {planner_json}\n"
        f"User query: {query}\n"
        "Return one JSON object now."
    )


def validate_llm_router_output(payload: dict) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return False, ["payload must be object"]
    if str(payload.get("query_type") or "") not in QUERY_TYPES:
        errors.append("invalid query_type")
    if str(payload.get("confidence") or "") not in CONFIDENCES:
        errors.append("invalid confidence")
    if not isinstance(payload.get("items"), list):
        errors.append("items must be a list")
    for idx, item in enumerate(payload.get("items") or []):
        if not isinstance(item, dict):
            errors.append(f"items[{idx}] must be object")
            continue
        if str(item.get("query_type") or payload.get("query_type") or "") not in QUERY_TYPES:
            errors.append(f"items[{idx}].query_type invalid")
        if str(item.get("confidence") or payload.get("confidence") or "") not in CONFIDENCES:
            errors.append(f"items[{idx}].confidence invalid")
        if str(item.get("goal") or "unknown") not in GOALS:
            errors.append(f"items[{idx}].goal invalid")
        if "product_oid" in item:
            errors.append(f"items[{idx}] must not contain product_oid")
    for key in ("needs_clarification",):
        if key in payload and not isinstance(payload.get(key), bool):
            errors.append(f"{key} must be boolean")
    return not errors, errors


def _normalize_llm_payload(payload: dict, query: str) -> dict[str, Any]:
    normalized = {key: payload.get(key) for key in ROUTER_SCHEMA_KEYS}
    normalized["query"] = str(normalized.get("query") or query)
    normalized["query_type"] = str(normalized.get("query_type") or "unknown")
    normalized["confidence"] = str(normalized.get("confidence") or "low")
    normalized["items"] = list(normalized.get("items") or [{"raw": query, "quantity": 1, "unit": None}])
    normalized["needs_clarification"] = bool(normalized.get("needs_clarification"))
    normalized["clarification_options"] = list(normalized.get("clarification_options") or [])
    normalized["unsupported_reason"] = normalized.get("unsupported_reason")
    normalized["reasons"] = list(normalized.get("reasons") or [])
    normalized["warnings"] = list(normalized.get("warnings") or [])
    return normalized


def route_query_with_llm(
    query: str,
    planner_output: dict | None = None,
    provider: str = "gemini",
    model: str | None = None,
    api_key: str | None = None,
    endpoint: str | None = None,
    timeout_seconds: int = DEFAULT_LLM_ROUTER_TIMEOUT_SECONDS,
) -> tuple[dict, dict]:
    selected_provider = provider if provider in {"gemini", "local_llm"} else "gemini"
    selected_model = model or (os.getenv("PROJECT2_GEMINI_MODEL") if selected_provider == "gemini" else os.getenv("PROJECT2_LOCAL_LLM_MODEL"))
    diagnostics = _base_diagnostics(selected_provider, selected_model)
    prompt = build_llm_router_prompt(query, planner_output)
    started = time.time()
    try:
        if selected_provider == "gemini":
            selected_key = api_key or os.getenv("GEMINI_API_KEY")
            selected_model = selected_model or "gemini-2.5-flash"
            diagnostics["llm_router_model"] = selected_model
            if not selected_key:
                raise RuntimeError("Missing GEMINI_API_KEY")
            url = endpoint or f"https://generativelanguage.googleapis.com/v1beta/models/{selected_model}:generateContent?key={selected_key}"
            payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0}}
            req = request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
            with request.urlopen(req, timeout=max(1, int(timeout_seconds))) as response:
                data = json.loads(response.read().decode("utf-8"))
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            diagnostics["llm_router_used"] = "gemini"
        else:
            selected_model = selected_model or "qwen3:4b"
            diagnostics["llm_router_model"] = selected_model
            url = endpoint or os.getenv("PROJECT2_LOCAL_LLM_ENDPOINT") or "http://localhost:11434/api/generate"
            payload = {"model": selected_model, "prompt": prompt, "stream": False, "options": {"temperature": 0}}
            req = request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
            with request.urlopen(req, timeout=max(1, int(timeout_seconds))) as response:
                data = json.loads(response.read().decode("utf-8"))
            text = data.get("response") or ""
            diagnostics["llm_router_used"] = "local_llm"
        parsed = _extract_json_object(text)
        diagnostics["llm_router_raw_output"] = parsed
        valid, errors = validate_llm_router_output(parsed)
        if not valid:
            diagnostics["llm_router_errors"].extend(errors)
            return {}, diagnostics
        return _normalize_llm_payload(parsed, query), diagnostics
    except Exception as exc:
        diagnostics["llm_router_used"] = "fallback"
        diagnostics["llm_router_errors"].append(str(exc))
        return {}, diagnostics
    finally:
        diagnostics["llm_router_latency_ms"] = round((time.time() - started) * 1000, 2)


def _norm(value: str) -> str:
    return normalize_product_name_for_lookup(value)


def _query_has_extra_clues(query: str, term: str) -> bool:
    nq = _norm(query)
    nt = _norm(term)
    return bool(nq and nt and nq != nt and len(nq) > len(nt) + 1)


def _append_merge_diagnostics(result: dict[str, Any], decision: str, strategy: str, llm_diag: dict[str, Any] | None = None) -> dict[str, Any]:
    diagnostics = dict(result.get("diagnostics") or {})
    if llm_diag:
        diagnostics.update({k: v for k, v in llm_diag.items() if k.startswith("llm_router_")})
    diagnostics["router_merge_strategy"] = strategy
    diagnostics["router_merge_decision"] = decision
    result["diagnostics"] = diagnostics
    result["warnings"] = list(result.get("warnings") or [])
    return result


def merge_rule_and_llm_router_outputs(rule_result: dict, llm_result: dict | None, strategy: str = "guarded") -> dict:
    result = dict(rule_result or {})
    if not llm_result:
        return _append_merge_diagnostics(result, "fallback", strategy)
    if strategy != "guarded":
        merged = dict(llm_result)
        return _append_merge_diagnostics(merged, "llm_accepted", strategy)

    query = str(result.get("query") or llm_result.get("query") or "")
    rule_type = str(result.get("query_type") or "unknown")
    llm_type = str(llm_result.get("query_type") or "unknown")
    llm_conf = str(llm_result.get("confidence") or "low")
    raw_terms = [str(item.get("raw") or query) for item in (result.get("items") or [{"raw": query}])]

    if rule_type == "unsupported_request" and str(result.get("confidence") or "") == "high":
        return _append_merge_diagnostics(result, "rule_kept", strategy)
    if rule_type == "not_covered_request" and any(_norm(term) in {_norm(v) for v in HARD_NOT_COVERED} for term in raw_terms):
        return _append_merge_diagnostics(result, "rule_kept", strategy)
    if rule_type == "ambiguous_request":
        for term in raw_terms:
            if _norm(term) in {_norm(v) for v in HIGH_RISK_SHORT} and not _query_has_extra_clues(query, term):
                return _append_merge_diagnostics(result, "rule_kept", strategy)
    if llm_type in {"subjective_recommendation", "unsupported_request"} and not (rule_type == "direct_product_search" and "?" in query):
        escalated = dict(llm_result)
        escalated["reasons"] = list(dict.fromkeys([*(result.get("reasons") or []), *(llm_result.get("reasons") or []), "llm escalated subjective/unsupported request"]))
        return _append_merge_diagnostics(escalated, "llm_accepted", strategy)
    if llm_conf == "low":
        return _append_merge_diagnostics(result, "rule_kept", strategy)
    if rule_type == "unknown" and llm_conf == "high":
        return _append_merge_diagnostics(dict(llm_result), "llm_accepted", strategy)
    compatible = rule_type == llm_type or {rule_type, llm_type} <= {"direct_product_search", "partial_product_search", "brand_search", "category_search", "basket_optimization"}
    if llm_conf == "high" and compatible:
        merged = dict(result)
        merged_items = []
        llm_items = list(llm_result.get("items") or [])
        for idx, item in enumerate(result.get("items") or []):
            merged_item = dict(item)
            if idx < len(llm_items):
                for key in ("brand", "category_hint", "product_clues", "goal"):
                    if llm_items[idx].get(key):
                        merged_item[key] = llm_items[idx].get(key)
            merged_items.append(merged_item)
        merged["items"] = merged_items or llm_items
        merged["confidence"] = result.get("confidence") if result.get("confidence") == "high" else llm_result.get("confidence")
        merged["reasons"] = list(dict.fromkeys([*(result.get("reasons") or []), *(llm_result.get("reasons") or [])]))
        return _append_merge_diagnostics(merged, "merged", strategy)
    return _append_merge_diagnostics(result, "rule_kept", strategy)
