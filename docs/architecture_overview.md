# Architecture Overview

## 1. System goals

Project2 aims to turn noisy grocery shopping requests into safer, more
explainable price-comparison results over monitored Macau supermarket data.

Goals:

- accept natural language shopping queries
- avoid dangerous substring mismatches
- distinguish covered / ambiguous / not-covered requests
- keep pricing and store decisions deterministic
- make optional LLM enhancement non-blocking

## 2. Why not pure keyword search

Pure keyword search is risky for retail data because many product names contain
misleading substrings:

- `糖` can refer to cooking sugar, candy, or `低糖`
- `油` can refer to cooking oil, sauces, or noodle flavors
- `雞蛋` can wrongly hit `雞蛋幼麵`

So the system cannot treat `product_name contains keyword` as authoritative.

## 3. Why not pure LLM

Pure LLM orchestration is also insufficient because:

- prices must come from monitored data, not model guesses
- store selection must be reproducible
- unsupported / subjective queries need guardrails
- ambiguity handling must be auditable

LLM features are optional helpers for routing or composition, not the source of
truth for prices or final product decisions.

## 4. Main architecture diagram

```text
User Query
  -> Query Intent Router
  -> Guardrails / Intent Taxonomy
  -> Route Selection
       -> direct product search
       -> brand search
       -> category / basket resolution
  -> Candidate Retrieval
       -> taxonomy retrieval
       -> RAG v2 retrieval
  -> SQLite Price Planner
  -> Decision Policy
  -> Response Composer
  -> Frontend Result Panel
  -> QA / Observability Loops
       -> regression pack
       -> observation log
       -> query review queue
       -> catalog confusion audit
       -> manual review workflow
```

## 5. Backend modules map

Core request / decision modules:

- `services/query_intent_router.py`
  - classify query shape into basket / direct / partial / brand / ambiguous /
    not-covered / unsupported routes
- `services/product_direct_search.py`
  - exact / partial / fuzzy-safe direct product search
- `services/brand_mining.py`
  - derive conservative brand aliases from the catalog
- `services/product_catalog_rag_v2.py`
  - deterministic candidate scoring and diagnostics
- `services/product_intent_resolver.py`
  - covered / ambiguous / not-covered resolution for generic product intents
- `services/product_oid_price_planner.py`
  - deterministic price planning from resolved product OIDs
- `services/shopping_decision_policy.py`
  - compare cheapest single-store / two-store / balanced strategies
- `services/agent_response_composer.py`
  - deterministic template output or optional Gemini composition

QA / data quality modules:

- `services/catalog_confusion_audit.py`
  - mine high-risk substring confusion across the full catalog
- `services/query_review_queue.py`
  - log uncertain or review-worthy query outcomes

## 6. Frontend modules map

- `frontend/src/components/ShoppingAgentBox.vue`
  - single main user input, advanced controls, submit / recalculate flow
- `frontend/src/components/AgentResultPanel.vue`
  - result rendering, clarification UI, debug / advanced surfaces
- `frontend/src/api.js`
  - frontend API wrapper for `/api/agent/shopping` and related endpoints

## 7. Request / response flow

1. Frontend posts `POST /api/agent/shopping`
2. Backend loads catalog / point context
3. Query router classifies the request
4. Matching guardrails decide whether to:
   - resolve directly
   - ask for clarification
   - mark not covered
   - reject unsupported subjective requests
5. Retrieval selects product candidates
6. SQLite planner calculates priceable plans
7. Decision policy picks best recommendation
8. Composer generates user-facing Chinese output
9. Frontend shows:
   - best plan
   - ambiguity prompts
   - not-covered messaging
   - optional debug information

## 8. Fallback behavior

- `planner_mode=local_llm` -> fallback to rule parsing if local LLM fails
- `llm_router_enabled=true` -> fallback to rule router if LLM output is low
  confidence or invalid
- `composer_mode=gemini` -> fallback to template composer if Gemini is missing
  or fails
- `retrieval_mode=taxonomy` remains the safest baseline

## 9. Observability and QA flow

- observation logging for agent execution diagnostics
- query review queue for uncertain or risky requests
- regression pack for stable acceptance cases
- CLI smoke tests for demo-safe behavior

## 10. Data quality loop

```text
catalog audit
  -> adversarial cases
  -> manual review
  -> reviewed strict cases
  -> regression pack
```

This lets the project grow guardrails from concrete catalog evidence instead of
only hand-picked sentinel examples.
