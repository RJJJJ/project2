# Catalog Confusion Audit

Phase 6.5 adds a deterministic audit layer for catalog-wide substring confusion.

## Goal

Find risky generic terms that appear inside unrelated product names, classify
them with explicit heuristics, and convert strong findings into adversarial
regression cases.

## Public surfaces

- `services/catalog_confusion_audit.py`
  - `load_catalog_for_confusion_audit`
  - `audit_confusion_terms`
  - `classify_term_occurrence`
  - `build_confusion_summary`
  - `generate_adversarial_cases_from_audit`
- `scripts/run_catalog_confusion_audit.py`
- `scripts/summarize_confusion_coverage.py`

## Default high-risk terms

`糖, 油, 米, 麵, 面, 奶, 水, 蛋, 雞蛋, 紙, 紙巾, 朱古力, 飲品, 茶, 咖啡, 鹽, 醬, 粉`

## Output files

- `data/eval/catalog_confusion_audit.json`
- `data/eval/catalog_confusion_audit_summary.md`
- `data/eval/catalog_adversarial_cases.json`
- `data/eval/confusion_coverage_summary.md`

## Workflow

1. Scan the catalog.
2. Classify term occurrences into true product vs attribute / flavor / modifier /
   different-category / ambiguous / needs-review buckets.
3. Generate strict adversarial cases only when deterministic rules are strong.
4. Mark uncertain cases as `needs_manual_label=true`.
5. Feed generated cases into the regression pack.

## Manual review workflow

Phase 6.6 adds a human-in-the-loop workflow for pending adversarial cases. The
goal is to let a reviewer promote stable cases into strict regression coverage
without letting the system guess labels automatically.

## How to export review queue

```powershell
python scripts\export_catalog_review_queue.py ^
  --adversarial-cases-path data\eval\catalog_adversarial_cases.json ^
  --audit-path data\eval\catalog_confusion_audit.json ^
  --output-csv data\eval\catalog_adversarial_review_queue.csv ^
  --output-md data\eval\catalog_adversarial_review_queue.md
```

The CSV is for Excel / Numbers / LibreOffice editing. The Markdown file is for
quick GitHub / VS Code review.

## How to fill review_decision

Leave `review_decision` blank when you want to keep the current state unchanged.
Otherwise fill one of:

- `promote_to_strict`
- `keep_pending`
- `ignore_case`
- `revise_expected`
- `needs_data_check`

`suggested_review_decision` is only a deterministic hint and never the final
label.

## Review decision meanings

- `promote_to_strict`: reviewed and safe to enforce in regression.
- `keep_pending`: still useful, but not ready for strict enforcement.
- `ignore_case`: skip this case in regression.
- `revise_expected`: expected JSON needs manual editing before promotion.
- `needs_data_check`: validate source catalog / taxonomy data first.

## How to apply labels

```powershell
python scripts\apply_catalog_review_labels.py ^
  --adversarial-cases-path data\eval\catalog_adversarial_cases.json ^
  --review-csv data\eval\catalog_adversarial_review_queue.csv ^
  --output-path data\eval\catalog_adversarial_cases_reviewed.json
```

This preserves original case fields and adds review metadata plus:

- `status = active | pending | ignored | needs_revision | needs_data_check`
- `enforce = true | false`

## How reviewed cases affect regression pack

`scripts/run_agent_regression_pack.py` now supports reviewed case files:

- `status=ignored` -> skipped and counted as ignored
- `enforce=true` or `needs_manual_label=false` -> treated as active strict cases
- `needs_manual_label=true` -> counted as pending manual label, not a failure
- `status=needs_revision` -> counted separately
- `status=needs_data_check` -> counted separately

## Recommended weekly workflow

1. Run catalog confusion audit.
2. Export review queue.
3. Human reviews the CSV.
4. Apply labels.
5. Run regression pack with reviewed cases.
6. Promote stable reviewed file into the repo as the current reviewed baseline.

## Scope boundary

- No large new dependencies.
- No LLM auto-judging of correctness.
- No automatic matching-logic rewrite unless a separate obvious bug is found.
