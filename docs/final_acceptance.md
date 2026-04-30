# Final Acceptance

This document lists the Phase 7 release-readiness checks for Project2.

## 1. Python tests

```powershell
python -m pytest -q -p no:cacheprovider
```

Pass criteria:

- all tests pass

## 2. Regression pack

```powershell
python scripts\run_agent_regression_pack.py ^
  --db-path data\app_state\project2_dev.sqlite3 ^
  --point-code p001 ^
  --output-dir data\eval ^
  --catalog-adversarial-cases-path data\eval\catalog_adversarial_cases_reviewed.json
```

Pass criteria:

- no crash
- base regression passes
- active strict catalog adversarial cases pass
- pending / ignored states are counted correctly

## 3. Frontend build

```powershell
cd frontend
npm run build
```

Pass criteria:

- build exits successfully
- `frontend/dist` generated or refreshed

## 4. Catalog confusion audit

```powershell
python scripts\run_catalog_confusion_audit.py ^
  --db-path data\app_state\project2_dev.sqlite3 ^
  --output-dir data\eval ^
  --generate-adversarial-cases
```

Pass criteria:

- audit JSON written
- summary Markdown written
- adversarial cases JSON written

## 5. Review queue export

```powershell
python scripts\export_catalog_review_queue.py ^
  --adversarial-cases-path data\eval\catalog_adversarial_cases.json ^
  --audit-path data\eval\catalog_confusion_audit.json ^
  --output-csv data\eval\catalog_adversarial_review_queue.csv ^
  --output-md data\eval\catalog_adversarial_review_queue.md
```

Pass criteria:

- CSV written
- Markdown written
- review columns included

## 6. API smoke test CLI

```powershell
python scripts\run_shopping_agent.py ^
  --query "我想買砂糖同洗頭水" ^
  --db-path data\app_state\project2_dev.sqlite3 ^
  --point-code p001 ^
  --include-price-plan ^
  --retrieval-mode rag_v2 ^
  --debug-json
```

Pass criteria:

- no crash
- `status = ok`
- resolved sugar + shampoo

## 7. Final acceptance runner

```powershell
python scripts\run_final_acceptance.py ^
  --db-path data\app_state\project2_dev.sqlite3 ^
  --point-code p001 ^
  --output-dir data\eval\final_acceptance
```

Optional skip for environments without Node build support:

```powershell
python scripts\run_final_acceptance.py ^
  --db-path data\app_state\project2_dev.sqlite3 ^
  --point-code p001 ^
  --output-dir data\eval\final_acceptance ^
  --skip-frontend-build
```

Expected outputs:

- `data/eval/final_acceptance/final_acceptance_results.json`
- `data/eval/final_acceptance/final_acceptance_summary.md`

Pass criteria:

- runner reports pass/fail/skipped honestly
- no hidden failures
- smoke tests summarized clearly
