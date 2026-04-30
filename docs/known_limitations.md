# Known Limitations

## 1. Data coverage limitations

- The project is based on public monitored Macau Consumer Council supermarket
  price data.
- It does **not** represent all supermarket SKUs.
- It does **not** provide real-time stock availability.
- It does **not** guarantee all in-store promotions are synchronized at the same
  time as the monitored dataset.
- `未收錄 / not_covered` means data unavailable in the monitored dataset, not
  that the supermarket never sells the product.

## 2. Subjective recommendation limitations

- No taste score
- No health score
- No popularity / sales volume score
- Subjective requests are redirected to supported alternatives instead of
  fabricated rankings

## 3. Price interpretation limitations

- Package sizes may differ across candidate products
- Unit-price normalization is not the main decision surface unless explicitly
  implemented for that path
- Cheapest total depends on monitored products, candidate matching, and selected
  `point_code`

## 4. LLM limitations

- LLM enhancements are optional
- Missing Gemini key or unavailable local LLM should trigger fallback behavior
- LLM does not control pricing
- LLM does not override deterministic guardrails

## 5. RAG limitations

- RAG v2 is currently deterministic lexical / scoring based
- Semantic embedding retrieval is future work, not current default behavior
- Rare abbreviations, slang, or under-specified product names may still fall
  into review queue or clarification paths

## 6. Manual review status

- Some catalog adversarial cases are still pending manual label
- A manual review workflow now exists to promote stable reviewed cases into
  strict regression coverage
