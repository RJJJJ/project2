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
4. `services/shopping_agent_orchestrator.py` combines the existing basket parser
   with the resolver and retriever. It is LLM-ready, but runs without an LLM key.

## Ambiguity handling

Terms such as sugar, oil, chocolate, tissue, noodle, rice, and milk can refer to
multiple monitored product classes. The agent returns `needs_clarification`
instead of forcing a possibly wrong match.

## Not-covered messaging

Known not-covered queries such as M&M, fries, and eggs return a clear message:
the public Consumer Council monitored dataset currently has no comparable price
record for that item. This does not mean the supermarket does not sell it.

## LLM does not calculate prices

Future LLM usage should be limited to:

- parsing messy natural language into structured item requests;
- asking a user-friendly clarification question;
- composing a grounded explanation from deterministic results.

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

## Future LLM hook

`run_shopping_agent(..., use_llm=True)` is reserved for a future planner/composer
hook. If no key is available, the current rule-first path still works and remains
the safe fallback.
