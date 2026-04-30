# Product Agent Design

Project2 is moving from plain keyword matching toward a small, deterministic
shopping-decision agent:

`User Query -> planner-style parsing -> rule-first intent taxonomy -> ambiguity /
not-covered detection -> controlled candidate retrieval -> deterministic SQL
price planning -> grounded response`

## Why not pure keyword matching

Product names contain misleading substrings. For example, "sugar" intent can be
confused with low-sugar soy milk, "oil" can appear in noodle flavors or sauces,
and "egg" can appear in egg noodles. Plain `product_name contains keyword`
therefore creates confident but wrong recommendations.

## Why not pure RAG

RAG can help retrieve possible product names, but price comparison must remain
deterministic. The system should not let an LLM invent prices, totals, store
coverage, or cheapest plans. Retrieval can assist candidate discovery; final
matching and optimization must be auditable Python / SQL.

## Rule-first + RAG-assisted + LLM-planned architecture

The stabilizing layers are:

1. `services/product_intent_taxonomy.py` defines known intents, positive terms,
   negative terms, category allowlists, ambiguity rules, and not-covered terms.
2. `services/product_intent_resolver.py` classifies each parsed item as
   `covered`, `ambiguous`, `not_covered`, or `unknown`.
3. `services/product_candidate_retriever.py` returns only products that satisfy
   the resolved intent rules.
4. `services/shopping_agent_orchestrator.py` combines the existing basket parser,
   resolver, retrieval, deterministic pricing, and final response composition.

## Ambiguity handling

Terms such as sugar, oil, chocolate, tissue, noodle, rice, and milk can refer to
multiple monitored product classes. The agent returns `needs_clarification`
instead of forcing a possibly wrong match.

## Not-covered messaging

Known not-covered queries such as M&M, fries, and eggs return a clear message:
the public Consumer Council monitored dataset currently has no comparable price
record for that item. This does not mean the supermarket does not sell it.

## LLM does not calculate prices

LLM usage is deliberately constrained:

- local LLM planner: parse messy natural language into structured shopping items;
- clarification UI: allow the user to disambiguate risky items;
- optional Gemini composer: rewrite the deterministic result into a more readable answer.

The LLM must not calculate prices, choose stores without SQL evidence, or invent
candidate products.

## Phase 2: deterministic pricing from resolved candidates

Phase 2 connects resolved agent candidates back to deterministic price planning:

1. The agent resolves only covered items into product intents.
2. The retriever attaches candidate products from the SQLite product catalog.
3. `services/shopping_agent_price_adapter.py` converts resolved items and top
   candidate products into priceable items.
4. `services/product_oid_price_planner.py` reads `price_records` directly and
   builds cheapest same-store plans by product OID.

Ambiguous and not-covered items stay in the response and do not participate in
price calculation. This allows partial pricing for already-resolved items while
still asking the user to clarify unsafe items.

`point_code` is required for price planning because supermarket availability and
price records are scoped to a collection point. Without a point, the agent can
still resolve product intents, but it cannot produce a grounded local price plan.

## Phase 3: local LLM planner + RAG-assisted retrieval + optional Gemini composer

### Why the local LLM only does planning

The local LLM planner converts a natural-language shopping request into a strict
JSON schema. It extracts item text, quantity, units, optimization hints, and
lightweight warnings. It does **not** resolve final `intent_id`, query SQLite,
calculate prices, or choose supermarkets.

### Pipeline expected schema

The planner output must follow this shape:

```json
{
  "task_type": "basket_price_optimization",
  "language": "zh-HK",
  "items": [
    {"raw": "?", "quantity": 1, "unit": "?", "notes": null}
  ],
  "optimization_goal": "cheapest",
  "location_hint": null,
  "confidence": "medium",
  "warnings": []
}
```

If the local LLM is unavailable, times out, returns invalid JSON, or uses the
wrong schema, the system falls back to the rule parser.

### Why RAG only does candidate augmentation

`retrieval_mode=rag_assisted` uses hybrid lexical scoring over product catalog
documents. It can improve candidate ranking for weak queries, but it is not the
authority for product intent. Taxonomy guardrails still decide whether an item
is covered, ambiguous, or not covered.

That means:

- ambiguous words such as `?`, `?`, `?`, `???`, `??`, `?`, and `?`
  still return clarification-first behavior;
- known not-covered queries such as `M&M`, `??`, and `??` stay not covered;
- RAG must not coerce `???? -> ??`, `???? -> ??`, or `M&M -> ???`.

### Why Gemini only does composition

`composer_mode=gemini` is optional and only rewrites the structured agent result
into user-facing Chinese. It cannot add items, alter prices, invent stores, or
remove clarification/not-covered warnings.

If `GEMINI_API_KEY` is missing, quota is exhausted, or the request fails, the
system falls back to the template composer.

### Fallback strategy

All Phase 3 capabilities are optional and safe by default:

- `planner_mode = rule | local_llm`
- `retrieval_mode = taxonomy | rag_assisted`
- `composer_mode = template | gemini`

Default production-safe configuration remains:

- `planner_mode = rule`
- `retrieval_mode = taxonomy`
- `composer_mode = template`

Every Phase 3 failure path must degrade gracefully without crashing.

## CLI examples

Baseline safe mode:

```bash
python scripts/run_shopping_agent.py   --query "??? ???? ???? ? ? M&M"   --db-path data/app_state/project2_dev.sqlite3   --point-code p001   --include-price-plan   --planner-mode rule   --retrieval-mode taxonomy   --composer-mode template   --debug-json
```

Local planner with fallback:

```bash
python scripts/run_shopping_agent.py   --query "????????????????????????"   --db-path data/app_state/project2_dev.sqlite3   --point-code p001   --include-price-plan   --planner-mode local_llm   --retrieval-mode taxonomy   --composer-mode template   --debug-json
```

RAG-assisted retrieval:

```bash
python scripts/run_shopping_agent.py   --query "?????????"   --db-path data/app_state/project2_dev.sqlite3   --point-code p001   --include-price-plan   --planner-mode rule   --retrieval-mode rag_assisted   --composer-mode template   --debug-json
```

Gemini composer with template fallback:

```bash
python scripts/run_shopping_agent.py   --query "?????????"   --db-path data/app_state/project2_dev.sqlite3   --point-code p001   --include-price-plan   --composer-mode gemini   --debug-json
```


## Phase 4: Decision Intelligence + Evaluation + Production Hardening

### Decision Policy Layer

Phase 4 adds `services/shopping_decision_policy.py` as a deterministic policy layer around the existing product-OID price planner. The public functions are:

- `build_decision_result(price_plan, policy, policy_options)`
- `compare_store_plans(store_plans, policy, policy_options)`
- `summarize_decision_result(decision_result)`

The old `price_plan.best_plan` remains compatible with the existing one-store UI. New recommendations are exposed at `price_plan.decision_result.best_recommendation`.

### `cheapest_two_stores` algorithm

`plan_cheapest_by_product_candidates_two_stores(...)` keeps the existing single-store planner intact and adds a small deterministic enumerator:

1. For each resolved priceable item, find the lowest-priced candidate product available in each supermarket.
2. Enumerate every one-store and two-store combination near the selected collection point.
3. For every item, choose the cheaper available store within that pair.
4. Keep only complete plans covering all priceable items.
5. Sort by estimated total, store count, and stable store identifiers.

The algorithm is intentionally simple because the expected store count near `p001` is small.

### `single_store_preferred`

This policy compares the best one-store plan and best max-two-store plan. By default, if the two-store plan is cheaper by **MOP 5.0 or less**, the system still recommends one store to reduce user effort. Override with:

```json
{ "single_store_threshold_mop": 5.0 }
```

### `balanced`

This policy scores complete one-/two-store plans with:

```text
score = estimated_total_mop + (store_count - 1) * extra_store_penalty_mop
```

The raw price remains in `estimated_total_mop`; the policy score is exposed only in diagnostics/debug surfaces. Default option:

```json
{ "extra_store_penalty_mop": 5.0 }
```

### Why LLM does not make price decisions

LLM components may parse shopping text or compose a user-readable explanation, but they must not calculate totals, select the cheapest plan, or override deterministic policy results. The Gemini composer prompt explicitly treats `price_plan.decision_result` as authoritative and forbids changing the recommendation, total, store count, or alternatives.

### Regression pack

`scripts/run_agent_regression_pack.py` runs fixed guardrail and acceptance queries for sugar/oil/noodle/chocolate/tissue ambiguity, not-covered items, RAG pollution checks, and price-plan availability.

Example:

```powershell
python scripts\run_agent_regression_pack.py --db-path data\app_state\project2_dev.sqlite3 --point-code p001 --output-dir data\eval
```

Outputs:

- `data/eval/agent_regression_results.json`
- `data/eval/agent_regression_summary.md`

### Observability JSONL

`services/agent_observability.py` builds compact structured observations containing planner/retrieval/composer modes, decision policy, price status, counts, totals, selected store count, latency, warnings, and errors.

CLI opt-in:

```powershell
python scripts\run_shopping_agent.py --query "我想買砂糖同洗頭水" --db-path data\app_state\project2_dev.sqlite3 --point-code p001 --include-price-plan --decision-policy balanced --log-observation --observation-log-path data\logs\agent_observations.jsonl --debug-json
```

API logging is disabled by default. It can be enabled with `PROJECT2_AGENT_OBSERVABILITY_LOG=1` and optionally `PROJECT2_AGENT_OBSERVABILITY_PATH`.

### CLI examples

```powershell
python scripts\run_shopping_agent.py --query "我想買砂糖同洗頭水" --db-path data\app_state\project2_dev.sqlite3 --point-code p001 --include-price-plan --decision-policy cheapest_single_store --debug-json
python scripts\run_shopping_agent.py --query "我想買砂糖同洗頭水" --db-path data\app_state\project2_dev.sqlite3 --point-code p001 --include-price-plan --decision-policy cheapest_two_stores --debug-json
python scripts\run_shopping_agent.py --query "我想買食油、朱古力飲品、牙膏" --db-path data\app_state\project2_dev.sqlite3 --point-code p001 --include-price-plan --decision-policy balanced --extra-store-penalty-mop 5 --debug-json
```

### Frontend decision policy selector

The Agent advanced controls now include Decision Policy:

- 最平一間店 (`cheapest_single_store`)
- 最平最多兩間店 (`cheapest_two_stores`)
- 優先一間店 (`single_store_preferred`)
- 平衡價格與少走路 (`balanced`)

Normal mode shows user-facing store names, store count, totals, item purchase locations, explanation text, and up to two alternatives. Debug mode shows policy diagnostics and raw `decision_result`. Internal `product_oid`, `supermarket_oid`, and intent IDs remain debug-only implementation details.

## Phase 5: Query Intelligence Router + Confidence + Review Queue

### Why Query Intent Router is needed

Real grocery queries are not always category names. Users may type a brand
(`出前一丁`), a near-product phrase (`出前一丁麻油味`), a full product name
(`麥老大雞蛋幼面`), a risky generic word (`麵`), or an unsupported preference
question (`最好吃的麵`). Phase 5 adds a deterministic router before product
resolution so the system chooses the correct search path instead of forcing
everything through category intent matching.

### Query types

`services/query_intent_router.py` emits:

- `basket_optimization`
- `direct_product_search`
- `partial_product_search`
- `brand_search`
- `category_search`
- `subjective_recommendation`
- `ambiguous_request`
- `not_covered_request`
- `unsupported_request`
- `unknown`

Each route includes `confidence`, per-item routing metadata, reasons, warnings,
and clarification flags.

### Confidence-based handling

High-confidence direct/partial product matches can be priced immediately.
Medium-confidence direct candidates are returned for confirmation. Low-confidence
or unknown routes can be logged to the review queue. High-risk short terms such
as `糖`, `油`, `米`, `麵`, `面`, `紙巾`, `雞蛋`, and `蛋` do not enter fuzzy
direct search.

### Direct product search

`services/product_direct_search.py` uses exact match, normalized exact match,
partial containment, token coverage scoring, and conservative stdlib `difflib`
fuzzy matching. Flavor tokens such as `麻油味` are weighted heavily, so
`出前一丁麻油味` ranks `出前一丁麻油味即食麵(袋裝)` ahead of unrelated
`出前一丁` flavors.

### Brand search

Brand-only queries such as `出前一丁` and `維他奶` return all currently
catalogued matching brand products. The system does not guess a flavor or
specification. If the goal is cheapest, the price planner compares the brand
candidates and picks the lowest available priced product.

User-facing copy says: `你沒有指定口味或規格。我先按目前公開資料中收錄的「品牌」商品比較價格。`

### Subjective recommendation guardrail

Queries such as `最好吃的麵`, `最健康的飲品`, or `推薦好用的洗頭水` are not
answered with fabricated taste, health, or rating claims. The composer explains
that the current source is public price data and offers supported alternatives:
find cheapest, list catalogued products, or compare by brand/category.

### Review queue

`services/query_review_queue.py` can build and append JSONL records for cases
that need product/routing review: unknown query type, low confidence, ambiguous /
unsupported / not-covered statuses, multiple direct candidates, fuzzy candidates
below high confidence, or user clarification answers.

CLI opt-in:

```powershell
python scripts\run_shopping_agent.py --query "出前一丁麻油味" --db-path data\app_state\project2_dev.sqlite3 --point-code p001 --include-price-plan --log-query-review --query-review-path data\logs\query_review_queue.jsonl --debug-json
```

Environment opt-in: `PROJECT2_QUERY_REVIEW_QUEUE=1`.

### Why LLM helps routing but does not price or decide products

The router is rule-first and deterministic by default. `query_router_mode=llm`
is reserved as a future extension, but the LLM must not invent products, prices,
stock, taste rankings, or health claims. Product matching remains auditable
catalog search; price decisions remain SQL-backed deterministic planning.
