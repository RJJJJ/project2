# Catalog Manual Review Workflow

This document describes the Phase 6.6 human review loop for catalog adversarial
cases.

## Purpose

Convert pending catalog confusion cases into reviewed regression assets without
changing the shopping-agent matching pipeline.

## Steps

1. Run the catalog confusion audit.
2. Export the pending review queue to CSV / Markdown.
3. Human reviewer fills `review_decision`, `review_notes`, `reviewer`,
   `reviewed_at`.
4. Apply labels to generate a reviewed JSON file.
5. Run regression using the reviewed JSON file.
6. Summarize review status and promote stable reviewed files.

## Commands

### Export review queue

```powershell
python scripts\export_catalog_review_queue.py ^
  --adversarial-cases-path data\eval\catalog_adversarial_cases.json ^
  --audit-path data\eval\catalog_confusion_audit.json ^
  --output-csv data\eval\catalog_adversarial_review_queue.csv ^
  --output-md data\eval\catalog_adversarial_review_queue.md
```

### Apply labels

```powershell
python scripts\apply_catalog_review_labels.py ^
  --adversarial-cases-path data\eval\catalog_adversarial_cases.json ^
  --review-csv data\eval\catalog_adversarial_review_queue.csv ^
  --output-path data\eval\catalog_adversarial_cases_reviewed.json
```

### Run regression with reviewed cases

```powershell
python scripts\run_agent_regression_pack.py ^
  --db-path data\app_state\project2_dev.sqlite3 ^
  --point-code p001 ^
  --output-dir data\eval ^
  --catalog-adversarial-cases-path data\eval\catalog_adversarial_cases_reviewed.json
```

### Summarize review status

```powershell
python scripts\summarize_catalog_review_status.py ^
  --cases-path data\eval\catalog_adversarial_cases_reviewed.json ^
  --output-path data\eval\catalog_review_status_summary.md
```

## Review decision values

- `promote_to_strict`
- `keep_pending`
- `ignore_case`
- `revise_expected`
- `needs_data_check`

## Weekly recommendation

1. Refresh catalog audit.
2. Export queue.
3. Review 5-20 pending cases.
4. Apply labels.
5. Rerun regression.
6. Commit reviewed JSON and summary artifacts when stable.
