# Project2：澳門超市格價助手 / AI 採購決策 Agent MVP

基於澳門消費者委員會公開超市價格資料的 AI 採購決策 Agent，可理解自然語言購物清單、處理商品歧義、判斷資料未收錄、比較不同採購策略並生成可解釋方案。

## 它解決什麼問題

一般格價工具常見問題是把使用者輸入直接做 keyword search，容易出現危險錯配，例如：

- `砂糖` 被錯配成 `低糖豆奶`
- `油` 被錯配成 `麻油味即食麵` 或 `蠔油`
- `雞蛋` 被錯配成 `雞蛋幼麵`

真實用戶也不只會輸入標準商品名，還會輸入：

- 口語購物清單
- 品牌名
- 不完整商品名
- 高風險泛詞
- 主觀問題（例如「最好吃的麵」）

Project2 用 **Query Intent Router + guardrails + RAG v2 + deterministic pricing**，把這些輸入分流到較安全、可解釋的決策路徑。

## Key capabilities

- Natural language shopping query
- Query intent router
- Ambiguity clarification
- Not-covered messaging
- Direct product search
- Brand search
- RAG v2 retrieval
- Deterministic price planner
- Decision policies
- Optional LLM / Gemini enhancement
- Regression pack
- Catalog confusion audit
- Manual review workflow

## Architecture overview

```text
User Query
  -> Query Intent Router
  -> Guardrails
  -> Direct / Brand / Category / Basket route
  -> RAG v2 / Candidate Retrieval
  -> SQLite Price Planner
  -> Decision Policy
  -> Composer
  -> Frontend Result Panel
  -> Observation / Review Queue / Regression
```

更多說明見：

- [`docs/architecture_overview.md`](docs/architecture_overview.md)
- [`docs/product_agent_design.md`](docs/product_agent_design.md)

## Data source and limitations

本專案目前使用 **澳門消費者委員會公開監測商品資料**。

這代表：

- 不代表所有超市 SKU
- 不代表即時庫存
- 不代表店內促銷完全同步
- `未收錄` 不代表超市沒有售賣
- 系統不提供口味、健康、銷量等主觀 / 非資料源支持的結論

詳細限制見：

- [`docs/known_limitations.md`](docs/known_limitations.md)

## Quick start

### Backend（Windows PowerShell）

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest -q -p no:cacheprovider
python scripts\run_api.py
```

API 預設：

- `http://127.0.0.1:8000`
- Swagger docs: `http://127.0.0.1:8000/docs`

### Frontend（Windows PowerShell）

```powershell
cd frontend
npm install
npm run dev
```

前端預設：

- `http://127.0.0.1:5173`

Build：

```powershell
cd frontend
npm run build
```

## Demo commands

### Agent CLI

```powershell
python scripts\run_shopping_agent.py ^
  --query "我想買砂糖同洗頭水" ^
  --db-path data\app_state\project2_dev.sqlite3 ^
  --point-code p001 ^
  --include-price-plan ^
  --retrieval-mode rag_v2 ^
  --debug-json
```

```powershell
python scripts\run_shopping_agent.py ^
  --query "出前一丁麻油味" ^
  --db-path data\app_state\project2_dev.sqlite3 ^
  --point-code p001 ^
  --include-price-plan ^
  --retrieval-mode rag_v2 ^
  --debug-json
```

### Regression pack

```powershell
python scripts\run_agent_regression_pack.py ^
  --db-path data\app_state\project2_dev.sqlite3 ^
  --point-code p001 ^
  --output-dir data\eval ^
  --catalog-adversarial-cases-path data\eval\catalog_adversarial_cases_reviewed.json
```

### Catalog confusion audit

```powershell
python scripts\run_catalog_confusion_audit.py ^
  --db-path data\app_state\project2_dev.sqlite3 ^
  --output-dir data\eval ^
  --generate-adversarial-cases
```

### Manual review queue export

```powershell
python scripts\export_catalog_review_queue.py ^
  --adversarial-cases-path data\eval\catalog_adversarial_cases.json ^
  --audit-path data\eval\catalog_confusion_audit.json ^
  --output-csv data\eval\catalog_adversarial_review_queue.csv ^
  --output-md data\eval\catalog_adversarial_review_queue.md
```

## Optional LLM setup

LLM / Gemini / Ollama 都是 **optional enhancement**，不是系統必需條件。

### Gemini

- 可用於 `composer_mode=gemini`
- 可用於 `llm_router_enabled=true`
- 如果沒有 API key 或呼叫失敗，系統會 fallback 到 deterministic / template 路徑

範例（不要把真實 key 寫進 repo）：

```powershell
$env:GEMINI_API_KEY="your-key"
```

### Local LLM / Ollama

- 可用於 `planner_mode=local_llm`
- 可用於 `llm_router_provider=local_llm`
- 如果本機模型 / endpoint 不可用，系統應 fallback，不應阻塞基本 demo

## Current validation status

As of latest local validation:

- `pytest`: `340 passed`
- regression pack with reviewed catalog adversarial cases:
  - `base_total: 32`
  - `catalog_adversarial_total: 54`
  - `active_strict: 12`
  - `pending_manual_label: 42`
  - `failed: 0`
- frontend build: passed
- review queue export: passed
- manual review apply workflow: passed

## Portfolio highlights

- Retail taxonomy design for ambiguous grocery queries
- Data quality guardrails against substring confusion
- RAG v2 retrieval with deterministic scoring diagnostics
- Deterministic decision system for store / price planning
- AI agent orchestration with optional LLM enhancement, not LLM dependency
- Frontend productization for demo-friendly and reviewer-friendly flows

## Documentation map

- [`docs/architecture_overview.md`](docs/architecture_overview.md)
- [`docs/agent_api_contract.md`](docs/agent_api_contract.md)
- [`docs/demo_guide.md`](docs/demo_guide.md)
- [`docs/final_acceptance.md`](docs/final_acceptance.md)
- [`docs/known_limitations.md`](docs/known_limitations.md)
- [`docs/portfolio_summary.md`](docs/portfolio_summary.md)
- [`docs/catalog_confusion_audit.md`](docs/catalog_confusion_audit.md)
- [`docs/catalog_manual_review_workflow.md`](docs/catalog_manual_review_workflow.md)
- [`docs/runbook.md`](docs/runbook.md)

## Known limitations

- Coverage only includes monitored public data, not full supermarket inventory
- Subjective recommendation queries are intentionally unsupported
- Cheapest plan depends on monitored products and selected `point_code`
- Some adversarial catalog cases are still pending manual review
- LLM features are optional and may fallback

詳見：

- [`docs/known_limitations.md`](docs/known_limitations.md)
