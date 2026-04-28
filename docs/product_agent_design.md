# Product Agent Design

Project2 is moving from plain keyword matching toward a small, deterministic
shopping-decision agent:

`User Query -> planner-style parsing -> rule-first intent taxonomy -> ambiguity /
not-covered detection -> controlled candidate retrieval -> deterministic SQL
price optimizer -> grounded response`

## Why not pure keyword matching

Product names contain many misleading substrings. For example, `糖` can appear in
`低糖豆奶`, `油` can appear in `麻油味即食麵`, and `雞蛋` can appear in `雞蛋幼面`.
Plain `product_name contains keyword` therefore creates confident but wrong
recommendations.

## Why not pure RAG

RAG can help retrieve possible product names, but price comparison must remain
deterministic. The system should not let an LLM invent prices, totals, store
coverage, or cheapest plans. Retrieval can assist candidate discovery; final
matching and optimization must be auditable Python / SQL.

## Rule-first + RAG-assisted + LLM-planned architecture

The first stabilizing layer is `services/product_intent_taxonomy.py`. It defines
known product intents, positive terms, negative terms, category allowlists, and
known not-covered queries.

The resolver in `services/product_intent_resolver.py` classifies each parsed item
as:

- `covered`
- `ambiguous`
- `not_covered`
- `unknown`

The retriever in `services/product_candidate_retriever.py` only returns products
that match the resolved intent rules. This prevents obvious false positives such
as low-sugar soy milk for cooking sugar.

The orchestrator in `services/shopping_agent_orchestrator.py` combines the
existing basket parser with the intent resolver and controlled retriever. It is
LLM-ready, but the current implementation runs without an LLM key.

## Ambiguity handling

Some user terms are intentionally ambiguous:

- `糖`: cooking sugar or candy
- `油`: cooking oil or seasoning oil
- `朱古力`: drink or snack
- `紙巾`: dry tissue or wet wipe
- `麵`: instant noodle, pasta, or dry noodle
- `米`: rice or rice noodle

The agent returns `needs_clarification` instead of forcing a possibly wrong
match.

## Not-covered messaging

Known not-covered queries such as `M&M`, `薯條`, and `雞蛋` return a clear message:
the public Consumer Council monitored dataset currently has no comparable price
record for that item. This does not mean the supermarket does not sell it.

## LLM does not calculate prices

Future LLM usage should be limited to:

- parsing messy natural language into structured item requests;
- asking a user-friendly clarification question;
- composing a grounded explanation from deterministic results.

The LLM must not calculate prices, choose stores without SQL evidence, or invent
candidate products.

## Future LLM hook

`run_shopping_agent(..., use_llm=True)` is intentionally reserved for a future
planner/composer hook. If no key is available, the current rule-first path still
works and remains the safe fallback.
