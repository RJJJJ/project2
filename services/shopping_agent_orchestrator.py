from __future__ import annotations

from pathlib import Path
from typing import Any

from services.agent_response_composer import compose_agent_response
from services.brand_mining import build_brand_alias_index
from services.llm_query_router import merge_rule_and_llm_router_outputs, route_query_with_llm
from services.local_llm_planner import normalize_planner_items, plan_query_with_local_llm, plan_query_with_rule_fallback, validate_planner_output
from services.product_candidate_retriever import retrieve_candidates_by_intent
from services.product_catalog_loader import load_products_from_sqlite
from services.product_catalog_rag import rag_assisted_retrieve_candidates
from services.product_catalog_rag_v2 import rag_v2_retrieve_candidates
from services.product_direct_search import search_brand_products, search_direct_products
from services.product_intent_resolver import normalize_query_text, resolve_product_intent
from services.product_intent_taxonomy import PRODUCT_INTENTS
from services.query_intent_router import route_user_query


def _candidate_summary(raw_name: str, intent_id: str | None, candidates: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    return {
        "raw_item_name": raw_name,
        "intent_id": intent_id,
        "intent_display_name_zh": PRODUCT_INTENTS.get(intent_id or "", {}).get("display_name_zh", intent_id),
        "candidates_count": len(candidates),
        "top_candidates": candidates[:5],
        **extra,
    }


def _clarification_options(intent_options: list[str]) -> list[dict[str, str]]:
    return [{"intent_id": intent_id, "label_zh": str(PRODUCT_INTENTS.get(intent_id, {}).get("display_name_zh") or intent_id)} for intent_id in intent_options]


def _status(resolved_items: list[dict[str, Any]], ambiguous_items: list[dict[str, Any]], not_covered_items: list[dict[str, Any]], unknown_items: list[dict[str, Any]], price_plan: dict[str, Any] | None = None, unsupported_items: list[dict[str, Any]] | None = None) -> str:
    if unsupported_items:
        return "unsupported"
    if ambiguous_items:
        return "needs_clarification"
    if price_plan:
        price_status = price_plan.get("status")
        if resolved_items and price_status == "ok" and not not_covered_items and not unknown_items:
            return "ok"
        if resolved_items and price_status in {"ok", "partial", "needs_clarification"} and (not_covered_items or unknown_items):
            return "partial"
        if not resolved_items and not_covered_items:
            return "not_covered"
    if resolved_items and (not_covered_items or unknown_items):
        return "partial"
    if not resolved_items and not_covered_items and not ambiguous_items and not unknown_items:
        return "not_covered"
    if resolved_items and not ambiguous_items and not not_covered_items and not unknown_items:
        return "ok"
    if unknown_items:
        return "needs_clarification"
    return "error"


def _normalized_clarification_answers(clarification_answers: dict[str, str] | None) -> dict[str, str]:
    answers: dict[str, str] = {}
    for raw_name, intent_id in (clarification_answers or {}).items():
        normalized_name = normalize_query_text(raw_name)
        normalized_intent = str(intent_id or "").strip()
        if normalized_name:
            answers[normalized_name] = normalized_intent
    return answers


def _user_clarification_resolution(raw_name: str, normalized_name: str, intent_id: str) -> dict[str, Any]:
    display_name = str(PRODUCT_INTENTS.get(intent_id, {}).get("display_name_zh") or intent_id)
    return {
        "raw_item_name": raw_name,
        "normalized_item_name": normalized_name,
        "status": "covered",
        "intent_id": intent_id,
        "intent_options": [],
        "reason": "user_clarification",
        "message_zh": f"\u5df2\u6839\u64da\u4f60\u7684\u9078\u64c7\uff0c\u5c07\u300c{raw_name}\u300d\u8996\u70ba\u300c{display_name}\u300d\u3002",
    }


def _parsed_items_from_planner_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for planned in payload.get("items") or []:
        raw_name = str(planned.get("raw") or "").strip()
        if not raw_name:
            continue
        quantity = planned.get("quantity")
        try:
            quantity_value = max(1, int(quantity if quantity is not None else 1))
        except (TypeError, ValueError):
            quantity_value = 1
        item: dict[str, Any] = {"keyword": raw_name, "quantity": quantity_value, "raw_text": raw_name}
        if planned.get("unit"):
            item["unit"] = str(planned.get("unit"))
        notes = str(planned.get("notes") or "").strip()
        if notes:
            item["notes"] = notes
        items.append(item)
    return items


def _plan_items(query: str, planner_mode: str, local_llm_model: str | None, local_llm_endpoint: str | None) -> tuple[list[dict[str, Any]], dict[str, Any], list[str], str]:
    planner_errors: list[str] = []
    normalized_mode = planner_mode if planner_mode in {"rule", "local_llm"} else "rule"
    if normalized_mode == "local_llm":
        try:
            planner_output = plan_query_with_local_llm(query, model=local_llm_model, endpoint=local_llm_endpoint)
            valid, errors = validate_planner_output(planner_output)
            if not valid:
                planner_errors.extend(errors)
                raise ValueError("; ".join(errors))
            normalized_output = normalize_planner_items(planner_output)
            return _parsed_items_from_planner_payload(normalized_output), normalized_output, planner_errors, "local_llm"
        except Exception as exc:
            planner_errors.append(str(exc))
            fallback_output = normalize_planner_items(plan_query_with_rule_fallback(query))
            return _parsed_items_from_planner_payload(fallback_output), fallback_output, planner_errors, "rule_fallback"
    planner_output = normalize_planner_items(plan_query_with_rule_fallback(query))
    return _parsed_items_from_planner_payload(planner_output), planner_output, planner_errors, "rule"


def _merge_candidates(primary: list[dict[str, Any]], fallback: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in [*primary, *fallback]:
        oid = str(candidate.get("product_oid") or "")
        key = oid or f"name::{candidate.get('product_name')}"
        if key in seen:
            for existing in merged:
                existing_key = str(existing.get("product_oid") or "") or f"name::{existing.get('product_name')}"
                if existing_key == key:
                    for diag_key in ("retrieval_mode", "rag_score", "rag_features", "penalties", "explanation_zh"):
                        if diag_key in candidate and diag_key not in existing:
                            existing[diag_key] = candidate[diag_key]
                    existing["matched_terms"] = list(dict.fromkeys([*(existing.get("matched_terms") or []), *(candidate.get("matched_terms") or [])]))
                    break
            continue
        seen.add(key)
        merged.append(candidate)
        if len(merged) >= max(0, int(limit)):
            break
    return merged


def _retrieve_candidates(products: list[dict[str, Any]], raw_name: str, intent_id: str, retrieval_mode: str, limit: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    taxonomy_candidates = retrieve_candidates_by_intent(products, intent_id, limit=limit)
    if retrieval_mode == "rag_v2":
        rag_candidates = rag_v2_retrieve_candidates(products, query=raw_name, intent_id=intent_id, limit=limit)
        merged_candidates = _merge_candidates(rag_candidates, taxonomy_candidates, limit)
        return merged_candidates, {"rag_used": True, "rag_candidate_count": len(rag_candidates), "rag_mode": "rag_v2"}
    if retrieval_mode != "rag_assisted":
        return taxonomy_candidates, {"rag_used": False, "rag_candidate_count": 0}
    rag_candidates = rag_assisted_retrieve_candidates(products, query=raw_name, intent_id=intent_id, limit=limit)
    merged_candidates = _merge_candidates(rag_candidates, taxonomy_candidates, limit)
    return merged_candidates, {"rag_used": True, "rag_candidate_count": len(rag_candidates)}


def _exploratory_unknown_candidates(products: list[dict[str, Any]], raw_name: str, retrieval_mode: str) -> list[dict[str, Any]]:
    if retrieval_mode == "rag_v2":
        return rag_v2_retrieve_candidates(products, query=raw_name, intent_id=None, limit=3)
    if retrieval_mode != "rag_assisted":
        return []
    return rag_assisted_retrieve_candidates(products, query=raw_name, intent_id=None, limit=3)


def run_shopping_agent(query: str, db_path: str | Path, point_code: str | None = None, use_llm: bool = False, debug: bool = False, include_price_plan: bool = False, price_strategy: str = "cheapest_single_store", max_candidates_per_item: int = 5, clarification_answers: dict[str, str] | None = None, planner_mode: str = "rule", local_llm_model: str | None = None, local_llm_endpoint: str | None = None, retrieval_mode: str = "taxonomy", composer_mode: str = "template", decision_policy: str | None = None, decision_policy_options: dict[str, Any] | None = None, query_router_mode: str = "hybrid", enable_query_review_queue: bool = False, query_review_path: str | Path = "data/logs/query_review_queue.jsonl", llm_router_enabled: bool = False, llm_router_provider: str = "gemini", llm_router_model: str | None = None, llm_router_options: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        products = load_products_from_sqlite(db_path)
        brand_index = build_brand_alias_index(products)
        parsed_items, planner_output, planner_errors, planner_used = _plan_items(query, planner_mode=planner_mode, local_llm_model=local_llm_model, local_llm_endpoint=local_llm_endpoint)
        normalized_router_mode = query_router_mode if query_router_mode in {"off", "rule", "hybrid", "llm"} else "hybrid"
        router_options = {"brand_index": brand_index}
        router_options.update(llm_router_options or {})
        router_decision = route_user_query(query, planner_output=planner_output if normalized_router_mode in {"hybrid", "llm"} else None, use_llm_router=normalized_router_mode == "llm", llm_router_options=router_options) if normalized_router_mode != "off" else {"query": query, "query_type": "basket_optimization", "confidence": "medium", "items": [], "needs_clarification": False, "clarification_options": [], "unsupported_reason": None, "reasons": ["router disabled"], "warnings": []}
        llm_router_diagnostics: dict[str, Any] = {
            "llm_router_provider": llm_router_provider,
            "llm_router_model": llm_router_model,
            "llm_router_used": "disabled",
            "llm_router_errors": [],
            "llm_router_raw_output": None,
            "router_merge_strategy": "guarded",
            "router_merge_decision": "disabled",
        }
        if llm_router_enabled:
            llm_result, llm_router_diagnostics = route_query_with_llm(
                query,
                planner_output=planner_output,
                provider=llm_router_provider,
                model=llm_router_model,
                api_key=(llm_router_options or {}).get("api_key"),
                endpoint=(llm_router_options or {}).get("endpoint"),
                timeout_seconds=int((llm_router_options or {}).get("timeout_seconds") or 20),
            )
            router_decision = merge_rule_and_llm_router_outputs(router_decision, llm_result, strategy="guarded")
            router_decision.setdefault("diagnostics", {}).update({k: v for k, v in llm_router_diagnostics.items() if k.startswith("llm_router_")})
            router_decision["diagnostics"]["router_merge_strategy"] = (router_decision.get("diagnostics") or {}).get("router_merge_strategy", "guarded")
            router_decision["diagnostics"]["router_merge_decision"] = (router_decision.get("diagnostics") or {}).get("router_merge_decision", "fallback")
        if normalized_router_mode != "off" and len(parsed_items) == 1 and len(router_decision.get("items") or []) == 1:
            router_raw = str((router_decision["items"][0] or {}).get("raw") or "").strip()
            parsed_raw = str(parsed_items[0].get("raw_text") or parsed_items[0].get("keyword") or "").strip()
            if router_raw and router_raw != parsed_raw and router_decision.get("query_type") in {"direct_product_search", "partial_product_search", "brand_search", "category_search", "subjective_recommendation", "unsupported_request", "not_covered_request", "ambiguous_request"}:
                parsed_items = [{"keyword": router_raw, "raw_text": router_raw, "quantity": router_decision["items"][0].get("quantity", 1), "unit": router_decision["items"][0].get("unit")}]
        router_items_by_raw = {str(item.get("raw") or ""): item for item in router_decision.get("items") or []}
        normalized_answers = _normalized_clarification_answers(clarification_answers)

        resolved_items: list[dict[str, Any]] = []
        ambiguous_items: list[dict[str, Any]] = []
        not_covered_items: list[dict[str, Any]] = []
        unsupported_items: list[dict[str, Any]] = []
        unknown_items: list[dict[str, Any]] = []
        candidate_summary: list[dict[str, Any]] = []
        warnings: list[str] = []
        rag_candidate_counts: dict[str, int] = {}
        rag_used = False

        for item in parsed_items:
            raw_name = str(item.get("raw_text") or item.get("keyword") or "").strip()
            if not raw_name:
                continue
            routed_item = router_items_by_raw.get(raw_name) or next((value for key, value in router_items_by_raw.items() if normalize_query_text(key) == normalize_query_text(raw_name)), {})
            routed_type = str(routed_item.get("query_type") or router_decision.get("query_type") or "")
            if router_decision.get("query_type") in {"subjective_recommendation", "unsupported_request"}:
                routed_type = str(router_decision.get("query_type"))
            normalized_name = normalize_query_text(raw_name)
            clarification_intent = normalized_answers.get(normalized_name)

            if routed_type in {"subjective_recommendation", "unsupported_request"}:
                unsupported_items.append({
                    "raw_item_name": raw_name,
                    "quantity": item.get("quantity", 1),
                    "unit": item.get("unit"),
                    "query_type": routed_type,
                    "message_zh": "目前資料主要是公開價格資料，沒有口味、健康程度、銷量、庫存或用戶評分資料，不能可靠判斷這類問題。",
                    "unsupported_reason": routed_item.get("unsupported_reason") or router_decision.get("unsupported_reason"),
                })
                continue

            if routed_type == "not_covered_request":
                resolution = {
                    "status": "not_covered",
                    "reason": "query_router_not_covered",
                    "message_zh": f"目前公開價格資料暫未收錄「{raw_name}」的可靠可比較價格。",
                }
                not_covered_items.append({"raw_item_name": raw_name, "quantity": item.get("quantity", 1), "unit": item.get("unit"), "resolution": resolution, "message_zh": resolution["message_zh"], "query_type": routed_type})
                continue

            if routed_type in {"direct_product_search", "partial_product_search"}:
                if retrieval_mode == "rag_v2":
                    direct = search_direct_products(products, raw_name, limit=20)
                    rag_matches = rag_v2_retrieve_candidates(products, query=raw_name, brand=routed_item.get("brand"), category_hint=routed_item.get("category_hint"), limit=20)
                    direct["matches"] = _merge_candidates(direct.get("matches") or [], rag_matches, 20)
                    if direct["matches"] and direct.get("confidence") == "low":
                        direct["confidence"] = "high" if float(direct["matches"][0].get("rag_score") or 0) >= 30 else "medium"
                        direct["status"] = "partial_match" if direct["confidence"] == "high" else "multiple_candidates"
                else:
                    direct = search_direct_products(products, raw_name, limit=20)
                matches = direct.get("matches") or []
                if matches and direct.get("confidence") == "high":
                    top_score = float(matches[0].get("match_score") or 0)
                    pricing_matches = [match for match in matches if float(match.get("match_score") or 0) >= max(0.88, top_score - 0.05)]
                    resolved_items.append({
                        "raw_item_name": raw_name,
                        "quantity": item.get("quantity", 1),
                        "unit": item.get("unit"),
                        "intent_id": None,
                        "intent_display_name_zh": None,
                        "query_type": routed_type,
                        "direct_search_status": direct.get("status"),
                        "candidates_count": len(pricing_matches),
                        "resolution_reason": direct.get("reason"),
                    })
                    candidate_summary.append(_candidate_summary(raw_name, None, pricing_matches, query_type=routed_type, direct_search={**direct, "matches": pricing_matches}))
                    continue
                if matches:
                    ambiguous_items.append({
                        "raw_item_name": raw_name,
                        "quantity": item.get("quantity", 1),
                        "unit": item.get("unit"),
                        "query_type": routed_type,
                        "message_zh": "我找到幾個相近商品，請確認是否是你想找的。",
                        "clarification_options": [
                            {"intent_id": str(match.get("product_oid")), "label_zh": str(match.get("product_name") or match.get("product_oid"))}
                            for match in matches[:5]
                        ],
                        "direct_search": direct,
                    })
                    candidate_summary.append(_candidate_summary(raw_name, None, matches, query_type=routed_type, direct_search=direct))
                    continue

            if routed_type == "brand_search":
                brand_term = str(routed_item.get("brand") or raw_name)
                if retrieval_mode == "rag_v2":
                    brand_matches = rag_v2_retrieve_candidates(products, raw_name, brand=brand_term, category_hint=routed_item.get("category_hint"), limit=20)
                    brand = {"status": "multiple_candidates" if brand_matches else "no_match", "raw_item_name": raw_name, "matches": brand_matches, "confidence": "high" if brand_matches else "low", "reason": "rag_v2 brand retrieval"}
                else:
                    brand = search_brand_products(products, brand_term, category_hint=routed_item.get("category_hint"), limit=20)
                matches = brand.get("matches") or []
                if matches:
                    resolved_items.append({
                        "raw_item_name": raw_name,
                        "quantity": item.get("quantity", 1),
                        "unit": item.get("unit"),
                        "intent_id": None,
                        "intent_display_name_zh": None,
                        "query_type": "brand_search",
                        "brand": brand_term,
                        "goal": routed_item.get("goal"),
                        "candidates_count": len(matches),
                        "resolution_reason": brand.get("reason"),
                    })
                    candidate_summary.append(_candidate_summary(raw_name, None, matches, query_type="brand_search", direct_search=brand))
                    warnings.append(f"你未指定「{brand_term}」的口味或規格，因此系統先在目前收錄的品牌商品中找最低價。")
                    continue

            if clarification_intent:
                if clarification_intent in PRODUCT_INTENTS:
                    resolution = _user_clarification_resolution(raw_name, normalized_name, clarification_intent)
                else:
                    warnings.append(f"Invalid clarification answer for {raw_name}: {clarification_intent}")
                    resolution = resolve_product_intent(raw_name)
            elif routed_type == "category_search" and routed_item.get("category_hint") in PRODUCT_INTENTS:
                resolution = {
                    "raw_item_name": raw_name,
                    "normalized_item_name": normalized_name,
                    "status": "covered",
                    "intent_id": routed_item.get("category_hint"),
                    "intent_options": [],
                    "reason": "query_router_category_hint",
                    "message_zh": f"已按查詢線索將「{raw_name}」視為「{PRODUCT_INTENTS.get(str(routed_item.get('category_hint')), {}).get('display_name_zh', routed_item.get('category_hint'))}」。",
                }
            else:
                resolution = resolve_product_intent(raw_name)

            enriched = {"raw_item_name": raw_name, "quantity": item.get("quantity", 1), "unit": item.get("unit"), "resolution": resolution}

            if resolution["status"] == "covered" and resolution.get("intent_id"):
                intent_id = str(resolution["intent_id"])
                candidates, retrieval_info = _retrieve_candidates(products, raw_name, intent_id, retrieval_mode, limit=20)
                rag_used = rag_used or bool(retrieval_info.get("rag_used"))
                rag_candidate_counts[raw_name] = int(retrieval_info.get("rag_candidate_count") or 0)
                display = PRODUCT_INTENTS.get(intent_id, {}).get("display_name_zh", intent_id)
                resolved_items.append({"raw_item_name": raw_name, "quantity": item.get("quantity", 1), "intent_id": intent_id, "intent_display_name_zh": display, "candidates_count": len(candidates), "resolution_reason": resolution.get("reason")})
                candidate_summary.append(_candidate_summary(raw_name, intent_id, candidates))
            elif resolution["status"] == "ambiguous":
                ambiguous_items.append(enriched | {"message_zh": resolution.get("message_zh"), "clarification_options": _clarification_options(list(resolution.get("intent_options") or []))})
            elif resolution["status"] == "not_covered":
                not_covered_items.append(enriched | {"message_zh": resolution.get("message_zh")})
            else:
                exploratory = _exploratory_unknown_candidates(products, raw_name, retrieval_mode)
                if exploratory:
                    rag_used = True
                    rag_candidate_counts[raw_name] = len(exploratory)
                unknown_items.append(enriched | {"message_zh": resolution.get("message_zh"), "risky": True, "exploratory_candidates": [candidate.get("product_name") for candidate in exploratory[:3]]})

        normalized_planner_mode = planner_mode if planner_mode in {"rule", "local_llm"} else "rule"
        normalized_retrieval_mode = retrieval_mode if retrieval_mode in {"taxonomy", "rag_assisted", "rag_v2"} else "taxonomy"
        normalized_composer_mode = composer_mode if composer_mode in {"template", "gemini"} else "template"
        status = _status(resolved_items, ambiguous_items, not_covered_items, unknown_items, unsupported_items=unsupported_items)
        diagnostics = {
            "products_loaded": len(products),
            "items_parsed": len(parsed_items),
            "resolved_count": len(resolved_items),
            "ambiguous_count": len(ambiguous_items),
            "not_covered_count": len(not_covered_items),
            "unknown_count": len(unknown_items),
            "unsupported_count": len(unsupported_items),
            "llm_planner_enabled": bool(use_llm),
            "debug": bool(debug),
            "clarification_answers_count": len(normalized_answers),
            "planner_mode": normalized_planner_mode,
            "planner_used": planner_used,
            "planner_errors": planner_errors,
            "retrieval_mode": normalized_retrieval_mode,
            "rag_used": rag_used,
            "rag_candidate_counts": rag_candidate_counts,
            "composer_mode": normalized_composer_mode,
            "decision_policy": decision_policy or price_strategy,
            "query_router_mode": normalized_router_mode,
            "query_type": router_decision.get("query_type"),
            "query_confidence": router_decision.get("confidence"),
            "llm_router_enabled": bool(llm_router_enabled),
            **{k: v for k, v in llm_router_diagnostics.items() if k != "llm_router_raw_output" or debug},
            **(router_decision.get("diagnostics") or {}),
        }
        if debug:
            diagnostics["planner_output"] = planner_output

        result = {"query": query, "point_code": point_code, "use_llm": use_llm, "status": status, "resolved_items": resolved_items, "ambiguous_items": ambiguous_items, "not_covered_items": not_covered_items, "unsupported_items": unsupported_items, "unknown_items": unknown_items, "candidate_summary": candidate_summary, "warnings": warnings, "diagnostics": diagnostics, "query_router": router_decision}
        if include_price_plan and status != "unsupported":
            from services.shopping_agent_price_adapter import build_agent_price_plan
            price_plan = build_agent_price_plan(
                result,
                db_path,
                point_code=point_code,
                strategy=price_strategy,
                max_candidates_per_item=max_candidates_per_item,
                decision_policy=decision_policy or price_strategy,
                decision_policy_options=decision_policy_options,
            )
            result["price_plan"] = price_plan
            result["status"] = _status(resolved_items, ambiguous_items, not_covered_items, unknown_items, price_plan, unsupported_items=unsupported_items)
            result["diagnostics"]["price_plan_status"] = price_plan.get("status")

        user_message_zh, composer_diagnostics = compose_agent_response(result, composer_mode=normalized_composer_mode)
        result["user_message_zh"] = user_message_zh
        result["composer_diagnostics"] = composer_diagnostics
        result["diagnostics"]["composer_used"] = composer_diagnostics.get("composer_used")
        result["diagnostics"]["composer_errors"] = composer_diagnostics.get("composer_errors") or []
        if enable_query_review_queue:
            from services.query_review_queue import append_query_review_record, build_query_review_record
            append_query_review_record(build_query_review_record(result), query_review_path)
        return result
    except Exception as exc:  # pragma: no cover
        fallback_result = {"query": query, "point_code": point_code, "use_llm": use_llm, "status": "error", "resolved_items": [], "ambiguous_items": [], "not_covered_items": [], "unknown_items": [], "candidate_summary": [], "warnings": [], "diagnostics": {"error": str(exc)}}
        user_message_zh, composer_diagnostics = compose_agent_response(fallback_result, composer_mode="template")
        fallback_result["user_message_zh"] = user_message_zh
        fallback_result["composer_diagnostics"] = composer_diagnostics
        return fallback_result
