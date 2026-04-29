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
