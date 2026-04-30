# LLM Router Eval Summary

generated_at: 2026-04-30T08:57:07.857991+00:00
provider: gemini
model: gemini-2.5-flash
total: 10
exact_query_type_match: 9
acceptable_match: 10
guardrail_violations: 0
fallback_count: 10
invalid_json_count: 0
pass_rate: 100.0
provider_unavailable: True

## Failed / fallback cases
- 出前一丁: actual=brand_search expected=['brand_search'] used=fallback errors=['Missing GEMINI_API_KEY']
- 出前一丁麻油味: actual=partial_product_search expected=['partial_product_search', 'direct_product_search'] used=fallback errors=['Missing GEMINI_API_KEY']
- 麥老大雞蛋幼面: actual=direct_product_search expected=['direct_product_search'] used=fallback errors=['Missing GEMINI_API_KEY']
- 雞蛋: actual=not_covered_request expected=['not_covered_request'] used=fallback errors=['Missing GEMINI_API_KEY']
- 最好吃的麵: actual=subjective_recommendation expected=['subjective_recommendation', 'unsupported_request'] used=fallback errors=['Missing GEMINI_API_KEY']
- 糖: actual=ambiguous_request expected=['ambiguous_request'] used=fallback errors=['Missing GEMINI_API_KEY']
- 油: actual=ambiguous_request expected=['ambiguous_request'] used=fallback errors=['Missing GEMINI_API_KEY']
- BB用嘅濕紙巾: actual=category_search expected=['category_search', 'partial_product_search'] used=fallback errors=['Missing GEMINI_API_KEY']
- 維他奶低糖豆奶: actual=partial_product_search expected=['direct_product_search', 'partial_product_search'] used=fallback errors=['Missing GEMINI_API_KEY']
- 最便宜的出前一丁: actual=brand_search expected=['brand_search'] used=fallback errors=['Missing GEMINI_API_KEY']
