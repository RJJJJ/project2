# Project2 Final Demo Checklist

## 1. Local validation

- [ ] python -m pytest -q -p no:cacheprovider
- [ ] python scripts/check_release_hygiene.py
- [ ] python scripts/weekly_data_refresh.py --skip-fetch --max-points 15 --categories 1-19
- [ ] cd frontend && npm.cmd run build

## 2. Demo data

- [ ] demo_data/processed has latest 15 points
- [ ] UPDATE_REPORT.md updated
- [ ] COVERAGE_REPORT.md updated
- [ ] FULL_CATEGORY_COVERAGE_REPORT.md updated
- [ ] WEEKLY_REFRESH_REPORT.md updated

## 3. Deployment

- [ ] Render backend deployed
- [ ] Vercel frontend deployed
- [ ] ALLOWED_ORIGINS correct
- [ ] VITE_API_BASE_URL correct
- [ ] scripts/smoke_check_deployment.py passes

## 4. Simple Mode UX

- [ ] Default mode is Simple Mode
- [ ] Mobile width readable
- [ ] No product_oid shown
- [ ] No provider / SQLite / JSONL shown
- [ ] Recommendation visible
- [ ] Total price visible
- [ ] Error message readable

## 5. Senior-friendly self test

- [ ] 12 checklist items completed
- [ ] At least 9 PASS
- [ ] At least 1 non-technical user tested, if available
- [ ] Top UX problem recorded

## 6. Git hygiene

- [ ] No data/raw committed
- [ ] No data/processed committed
- [ ] No project2_dev.sqlite3 committed
- [ ] No node_modules committed
- [ ] No .venv committed
- [ ] Commit message meaningful, e.g. Prepare v1.0 demo stabilization

## 7. Known limitations to mention in demo

- [ ] Data from public Consumer Council source
- [ ] Prices may differ from in-store prices
- [ ] 500m radius fixed for now
- [ ] Web alert center is not real push
- [ ] SQLite / Gemini / Agent are prototypes
- [ ] No real auth yet

## 45-point expansion readiness

- [ ] 45 candidate points captured
- [ ] names/districts reviewed
- [ ] dst values reviewed
- [ ] dry-run passed
- [ ] full fetch passed
- [ ] coverage report passed
- [ ] SQLite import passed
- [ ] data size reviewed before demo_data sync
