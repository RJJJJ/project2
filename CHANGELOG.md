# Changelog

All notable MVP presentation-package changes are tracked here.

## v1.0-simple - Senior-friendly Simple Mode

### Added

- Senior-friendly simple mode as the default frontend mode.
- Larger recommendation and item cards for the core flow.
- Simplified recommendation copy focused on where to buy, total price, and reason.
- Optional product specification flow behind `想指定品牌 / 規格？`.

### Notes

- Advanced mode keeps the existing candidate UX, watchlist, alerts, historical signals, feedback, server mode, and technical details.
- No LLM, database, crawler, optimizer, backend API, deployment config, or data pipeline changes.

## v0.9 - Server-side MVP Readiness Batch

### Added

- Server-side watchlist JSON prototype under `data/app_state/watchlists.json`.
- User token mode for separating prototype users without formal login.
- Alert history API for viewed / dismissed alert status.
- User watchlist CRUD APIs.
- Frontend local / server mode switch with optional local watchlist sync.

### Notes

- v0.9 still avoids formal login, database adoption, real push delivery, crawler changes, optimizer changes, and Telegram Bot changes.

## v0.7 - User Testing Readiness Batch

### Added

- Onboarding: compact “如何使用” instructions and public-price disclaimer in the web demo.
- Demo examples: quick-test buttons for common daily baskets.
- Feedback localStorage: browser-only feedback form with view, download JSON, and clear actions.
- Error diagnostics: collapsible technical details for API endpoint, HTTP status, error message, and suggestions.
- User testing guide: `USER_TESTING_GUIDE.md` for small-scale real-user trials.

### Notes

- v0.7 keeps the no-login, no-database, no-LLM, no-real-push MVP boundary.

## v0.6 - MVP Productization Batch

### Added

- Watchlist alerts: `/api/watchlist/alerts` generates alert candidates from watched products.
- Historical signals: historical low, below-average, and unusual-high price signal surface.
- Weekly demo data update report coverage for historical signals and alert smoke tests.
- Deployment smoke check: `scripts/smoke_check_deployment.py` validates deployed backend API endpoints.
- Productized watchlist panel grouping watched items, price status, and alert candidates.

### Notes

- v0.6 still avoids LLM, login, database, real push delivery, crawler changes, optimizer changes, and Telegram Bot changes.

## 2026-04-27

### Added

- MVP demo script with live web and API documentation links.
- MVP roadmap covering near-term and later milestones.
- Screenshot capture guide under `docs/screenshots/README.md`.

### Changed

- README now surfaces the deployed web demo and API docs URLs near the top.

### Notes

- This changelog is for presentation/package documentation only.
- Backend code, frontend code, crawler, optimizer, deployment config, and data files were intentionally left unchanged.

## 2026-04-28 - 15-point coverage QA and point search

### Added

- 15-point coverage report script producing `COVERAGE_REPORT.md` and `data/reports/coverage_report.json` from processed JSONL.
- Searchable grouped point selector in the frontend, grouped by district and searchable by name, district, or point code.

### Notes

- No LLM, database, crawler-core, optimizer-flow, Telegram Bot, deployment-config, radius, or 45-point expansion changes.
