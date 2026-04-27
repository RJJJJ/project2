# Changelog

All notable MVP presentation-package changes are tracked here.

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
