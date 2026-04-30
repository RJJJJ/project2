# Portfolio Summary

## 1. 30-second pitch

Project2 is an AI-assisted supermarket price decision system for Macau monitored
retail data. Instead of naive keyword matching, it routes natural-language
queries through retail guardrails, candidate retrieval, and deterministic price
planning so the final answer is safer, more explainable, and easier to QA.

## 2. Problem

Retail search is deceptively hard:

- product names contain misleading substrings
- users type incomplete names, brands, or conversational requests
- subjective questions should not trigger fake recommendations
- price comparison must stay grounded in actual monitored data

## 3. Solution

Project2 combines:

- Query Intent Router
- retail taxonomy / guardrails
- direct product and brand search
- deterministic RAG v2 scoring
- SQLite-backed price planning
- decision policies for store recommendations
- regression and catalog audit workflows

## 4. Technical highlights

- AI agent orchestration around a deterministic core
- Query Intent Router for route-safe handling
- Product taxonomy design for ambiguous grocery language
- RAG v2 retrieval with interpretable scoring
- Deterministic price planning from monitored data
- Decision policy layer for one-store vs two-store tradeoffs
- Catalog-wide confusion audit and adversarial case generation
- Regression pack and manual-review workflow
- Frontend productization for demo and reviewer clarity

## 5. Why this is not just a CRUD app

This project is not only storing and displaying prices. It solves:

- natural-language understanding
- retail ambiguity handling
- safe fallback behavior
- explainable retrieval and pricing logic
- evaluation and release QA loops

## 6. What I learned / engineering tradeoffs

- deterministic systems are critical when prices and recommendations must be
  auditable
- optional LLM enhancement is often better than LLM dependency
- retrieval quality needs both taxonomy constraints and regression protection
- productization requires docs, demo readiness, and QA workflows, not only core
  features

## 7. Future improvements

- semantic retrieval / embeddings as an optional retrieval lane
- stronger package-size normalization
- richer user-side comparison UI
- broader monitored data coverage
- continued manual promotion of reviewed adversarial cases into strict
  regression coverage
