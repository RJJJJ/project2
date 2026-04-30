# Runbook

## Start backend

```powershell
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts\run_api.py
```

Backend:

- base URL: `http://127.0.0.1:8000`
- docs: `http://127.0.0.1:8000/docs`

## Start frontend

```powershell
cd frontend
npm install
npm run dev
```

## Refresh data

If you need to refresh the demo fallback dataset:

```powershell
python scripts\update_demo_data.py --max-points 46 --preset demo_daily
```

Weekly refresh flow:

```powershell
python scripts\weekly_data_refresh.py --max-points 46 --categories 1-19
```

## Run regression

```powershell
python scripts\run_agent_regression_pack.py ^
  --db-path data\app_state\project2_dev.sqlite3 ^
  --point-code p001 ^
  --output-dir data\eval ^
  --catalog-adversarial-cases-path data\eval\catalog_adversarial_cases_reviewed.json
```

## Run catalog audit

```powershell
python scripts\run_catalog_confusion_audit.py ^
  --db-path data\app_state\project2_dev.sqlite3 ^
  --output-dir data\eval ^
  --generate-adversarial-cases
```

## Review manual labels

Export:

```powershell
python scripts\export_catalog_review_queue.py ^
  --adversarial-cases-path data\eval\catalog_adversarial_cases.json ^
  --audit-path data\eval\catalog_confusion_audit.json ^
  --output-csv data\eval\catalog_adversarial_review_queue.csv ^
  --output-md data\eval\catalog_adversarial_review_queue.md
```

Apply:

```powershell
python scripts\apply_catalog_review_labels.py ^
  --adversarial-cases-path data\eval\catalog_adversarial_cases.json ^
  --review-csv data\eval\catalog_adversarial_review_queue.csv ^
  --output-path data\eval\catalog_adversarial_cases_reviewed.json
```

## Enable Gemini

```powershell
$env:GEMINI_API_KEY="your-key"
```

Use with:

- `composer_mode=gemini`
- `llm_router_enabled=true`

## Enable Ollama / local LLM

Example usage:

```powershell
python scripts\run_shopping_agent.py ^
  --query "我想買砂糖同洗頭水" ^
  --planner-mode local_llm ^
  --local-llm-endpoint http://127.0.0.1:11434 ^
  --local-llm-model qwen3:4b
```

LLM features are optional and should fallback if unavailable.

## Troubleshooting

### Missing DB

- verify `data\app_state\project2_dev.sqlite3` exists
- rerun SQLite import if needed:

```powershell
python scripts\import_processed_to_sqlite.py --date latest --max-points 46
```

### Frontend build fails

- ensure Node / npm is installed
- run:

```powershell
cd frontend
npm install
npm run build
```

### Gemini key missing

- template composer and rule router should still work
- verify you are not assuming Gemini is required for demo

### Ollama unavailable

- switch back to `planner_mode=rule`
- disable local LLM router path

### Regression failed

- inspect:
  - `data/eval/agent_regression_results.json`
  - `data/eval/agent_regression_summary.md`
- check whether failure came from:
  - base regression
  - active strict catalog adversarial cases
  - reviewed-case state mismatch
