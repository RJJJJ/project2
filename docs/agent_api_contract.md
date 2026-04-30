# Agent API Contract

## Endpoint

```text
POST /api/agent/shopping
```

This is the user-facing single source of truth for the shopping agent flow.

## Request fields

### Required

- `query: string`
  - natural-language shopping query

### Optional

- `point_code: string | null`
  - collection point code, e.g. `p001`
  - default behavior depends on caller / backend configuration
- `use_llm: boolean = false`
  - legacy flag; core pricing does not depend on it
- `include_price_plan: boolean = false`
  - whether to attach deterministic price planning output
- `price_strategy: string = "cheapest_single_store"`
  - current default strategy input
- `decision_policy: string = "cheapest_single_store"`
  - supported:
    - `cheapest_single_store`
    - `cheapest_two_stores`
    - `single_store_preferred`
    - `balanced`
- `decision_policy_options: object | null`
  - e.g. `single_store_threshold_mop`, `extra_store_penalty_mop`
- `planner_mode: string = "rule"`
  - `rule | local_llm`
- `retrieval_mode: string = "taxonomy"`
  - `taxonomy | rag_assisted | rag_v2`
- `composer_mode: string = "template"`
  - `template | gemini`
- `clarification_answers: object | null`
  - map from ambiguous item text to selected `intent_id`
- `query_router_mode: string = "hybrid"`
  - `off | rule | hybrid | llm`
- `llm_router_enabled: boolean = false`
- `llm_router_provider: string = "gemini"`
  - `gemini | local_llm`
- `llm_router_model: string | null`
- `llm_router_options: object | null`

## Response fields

Top-level response fields returned by the current backend:

- `query`
- `point_code`
- `status`
- `resolved_items`
- `ambiguous_items`
- `not_covered_items`
- `unsupported_items`
- `unknown_items`
- `candidate_summary`
- `warnings`
- `diagnostics`
- `query_router`
- `price_plan`
- `user_message_zh`
- `composer_diagnostics`

Important derived fields:

- `query_type` lives at `query_router.query_type`
- `decision_result` lives at `price_plan.decision_result`

## Response conventions

### `status`

Possible values:

- `ok`
- `partial`
- `needs_clarification`
- `not_covered`
- `unsupported`
- `error`

Meaning:

- `ok`: the system resolved enough items to generate a usable answer / plan
- `partial`: some items resolved, some did not
- `needs_clarification`: user input is ambiguous and must be narrowed
- `not_covered`: requested item is outside current monitored dataset coverage
- `unsupported`: subjective or unsupported request type
- `error`: unexpected failure

### `query_type`

Possible values:

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

### `price_plan.best_plan` vs `price_plan.decision_result.best_recommendation`

- `price_plan.best_plan`
  - direct deterministic planner output
- `price_plan.decision_result.best_recommendation`
  - policy-aware final recommendation

For UI / product usage, prefer `decision_result.best_recommendation`.

### Clarification behavior

If `status = needs_clarification`, the response may still include partial pricing
for already confirmed items, but unresolved items must stay unresolved until the
user clarifies them.

### Not-covered behavior

`not_covered` means the item is unavailable in the current monitored dataset. It
does **not** mean supermarkets never sell it.

### UI exposure

Internal identifiers such as `product_oid` may appear in debug payloads but
should not be emphasized in the normal user-facing UI.

## Sample request / response sketches

### 1. 我想買砂糖同洗頭水

Request:

```json
{
  "query": "我想買砂糖同洗頭水",
  "point_code": "p001",
  "include_price_plan": true,
  "retrieval_mode": "rag_v2"
}
```

Expected response shape:

```json
{
  "status": "ok",
  "query_router": {
    "query_type": "basket_optimization"
  },
  "resolved_items": [
    {"raw_item_name": "砂糖", "intent_id": "cooking_sugar"},
    {"raw_item_name": "洗頭水", "intent_id": "shampoo"}
  ],
  "ambiguous_items": [],
  "not_covered_items": [],
  "price_plan": {
    "status": "ok",
    "decision_result": {
      "policy": "cheapest_single_store",
      "best_recommendation": {}
    }
  },
  "user_message_zh": "..."
}
```

### 2. 出前一丁

Expected:

```json
{
  "status": "ok",
  "query_router": {
    "query_type": "brand_search"
  },
  "resolved_items": [
    {"raw_item_name": "出前一丁", "query_type": "brand_search"}
  ],
  "candidate_summary": [
    {"query_type": "brand_search", "top_candidates": []}
  ]
}
```

### 3. 出前一丁麻油味

Expected:

```json
{
  "status": "ok",
  "query_router": {
    "query_type": "partial_product_search"
  },
  "candidate_summary": [
    {
      "query_type": "partial_product_search",
      "top_candidates": [
        {"product_name": "出前一丁麻油味即食麵(袋裝)"}
      ]
    }
  ]
}
```

### 4. 最好吃的麵

Expected:

```json
{
  "status": "unsupported",
  "query_router": {
    "query_type": "subjective_recommendation"
  },
  "unsupported_items": [
    {"raw_item_name": "最好吃的麵"}
  ],
  "user_message_zh": "..."
}
```

### 5. 雞蛋

Expected:

```json
{
  "status": "not_covered",
  "query_router": {
    "query_type": "not_covered_request"
  },
  "not_covered_items": [
    {"raw_item_name": "雞蛋"}
  ],
  "candidate_summary": []
}
```
