# MVP Roadmap

## Current MVP

- Public web demo deployed on Vercel.
- Public FastAPI backend deployed on Render.
- Demo data flow based on processed JSONL price data.
- Basket parsing and shopping recommendation flow suitable for stakeholder review.

## Near-term improvements

### Product experience

- Improve empty, loading, and error states in the web demo.
- Add clearer explanation of recommendation logic in the UI.
- Add demo-friendly examples for common Macau shopping baskets.
- Capture and publish screenshots listed in `docs/screenshots/README.md`.

### Data quality

- Document data freshness and source update cadence.
- Add visible timestamps for the dataset used by each recommendation.
- Expand validation around missing prices, aliases, and unavailable items.

### API maturity

- Stabilize request/response examples in the API docs.
- Add explicit health and readiness checks for deployment monitoring.
- Add versioning notes for public API changes.

## Later milestones

- Broader product alias coverage.
- More collection-point and neighborhood scenarios.
- Route-aware or distance-aware recommendation improvements.
- User feedback capture for incorrect matches or recommendations.
- Production observability for latency, errors, and data refresh status.

## Out of scope for MVP

- Real checkout or inventory reservation.
- Guaranteed live shelf availability.
- Full-map route optimization.
- Payment, accounts, or personalized shopping history.
