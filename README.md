# 澳門採購決策 Agent MVP

本專案是一個本地採購決策 MVP，用 processed JSONL 價格資料，為指定採集點附近約 500 米的購物清單產生採購方案，並提供本區價差訊號。

## Live MVP

- Live Web Demo URL: https://project2-three-rho.vercel.app
- Live API Docs: https://macau-shopping-api.onrender.com/docs

## 商品候選確認

Web Demo 支援「先選商品規格」：系統會推薦常見規格（例如米類 5公斤 / 10公斤家庭包裝），用戶仍可自行改選或選擇不指定。

## 目前功能總覽

- 多地區比價：以採集點 / 地區切換附近超市價格資料。
- 商品候選確認：先選商品規格後再生成方案，避免規格誤配。
- 系統推薦常見規格：候選商品會考慮常見規格、覆蓋與價格。
- 本區價差訊號：比較同日同區超市價差。
- 歷史抵買訊號：用 processed historical data 判斷接近低價、低於均價與異常偏高。
- Watchlist 收藏商品：Web Demo 以 browser localStorage 保存關注商品。
- Alert Rules 提醒候選：根據關注商品與價格訊號生成「是否值得提醒」候選，不做真正推送。
- User Testing Readiness：頁面內建「如何使用」、快速測試 examples、feedback localStorage 與錯誤技術詳情。
- Weekly Demo Data Update：每週 demo data update workflow 產生驗收 report。

## 小範圍試用

- 試用說明：[`USER_TESTING_GUIDE.md`](USER_TESTING_GUIDE.md)
- Demo examples：Web Demo 的「快速測試」提供基本日用品、清潔用品、飲食基本三組測試輸入。
- Feedback localStorage：`macau-shopping-feedback-v1`，可在 Web Demo 內查看、下載 JSON 或清空。

## 本機模式 vs 雲端測試模式

Web Demo 預設使用「本機模式」，watchlist / feedback 保存在 browser localStorage，不需要登入。

v0.9 新增「雲端測試模式」：

- 使用簡單 `user_token` 區分測試用戶，例如 `demo-user-token`。
- `user_token` 只是 demo token，不是正式登入、密碼、email 或 OAuth。
- Watchlist 與 alert history 會寫入 backend JSON file：`data/app_state/watchlists.json`。
- Server-side JSON store 僅供 MVP / App / 推送流程原型測試，正式版應改用持久 DB 與真正 auth。

## 部署後 smoke check

```bash
python scripts/smoke_check_deployment.py --base-url https://macau-shopping-api.onrender.com
```

Output example:

```json
{
  "base_url": "https://macau-shopping-api.onrender.com",
  "ok": true,
  "checks": [
    {"name": "health", "ok": true, "status_code": 200, "error": null}
  ],
  "errors": []
}
```

## 快速開始

先建立環境設定：

```bash
copy .env.example .env
```

檢查本地狀態：

```bash
python scripts/dev_check.py
```

Windows 可查看一鍵開發啟動提示：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_dev.ps1
```

## 生成 Demo Data

如果尚未有 processed data，先抓取前 5 個採集點：

```bash
python scripts/fetch_demo_points.py --max-points 5 --preset demo_daily
```

檢查多地區 MVP 是否可用：

```bash
python scripts/verify_demo_points.py --max-points 5 --preset demo_daily --write-report
```

## 啟動 FastAPI

```bash
python scripts/run_api.py
```

預設 API base URL：

```text
http://127.0.0.1:8000
```

## 啟動 Web Demo

```bash
cd frontend
npm install
npm run dev
```

前端預設連接：

```text
http://127.0.0.1:8000
```

如需改 API URL，可設定：

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

`frontend/.env.example` 也提供本地前端設定範本：

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

部署到 Vercel 時，請在 Vercel 專案環境變數設定：

```text
VITE_API_BASE_URL=https://your-render-backend.onrender.com
```

Render backend 若要允許 Vercel frontend 呼叫，請設定：

```text
ALLOWED_ORIGINS=https://your-vercel-app.vercel.app
```

## 啟動 Telegram Bot

先在 `.env` 填入：

```text
TELEGRAM_BOT_TOKEN=你的 Telegram bot token
DEFAULT_POINT_CODE=p001
DEFAULT_DATE=latest
```

再使用現有 Telegram Bot 入口啟動。常用指令：

```text
/check 我想買一包米、兩支洗頭水、一包紙巾
/check p001 我想買一包米、兩支洗頭水
/signals p001
/signals p001 10
/point 高士德
```

## 多地區驗收

```bash
python scripts/inspect_collection_points.py
python scripts/verify_demo_points.py --max-points 5 --preset demo_daily --write-report
```

報告會輸出到：

```text
POINT_TEST_REPORT.md
```

## Web Demo 截圖驗收 Checklist

- API 已啟動：`python scripts/run_api.py`
- 前端已啟動：`cd frontend && npm run dev`
- 地區可以載入，並預設顯示 `p001`
- 點擊「生成採購方案」後可看到推薦方案、總價、建議超市與商品明細
- 「本區價差訊號」可顯示最多 5 個價差商品卡片

## 常見問題

### Failed to fetch

通常是 backend 未啟動或 API base URL 不一致。先確認：

```bash
python scripts/run_api.py
```

再確認前端使用的 `VITE_API_BASE_URL` 是否指向 `http://127.0.0.1:8000`。如果瀏覽器顯示 CORS 錯誤，確認前後端都在本機預期位址啟動。

### 找不到 processed data

先跑 demo data：

```bash
python scripts/fetch_demo_points.py --max-points 5 --preset demo_daily
```

再跑：

```bash
python scripts/dev_check.py
```

### PowerShell 8009001d

這是本機 PowerShell 啟動或系統憑證相關錯誤。可改用 CMD 執行同樣命令，例如：

```cmd
python scripts/run_api.py
cd frontend
npm run dev
```

## 更新部署 Demo Data

一條命令抓取前 5 個 collection point 的 `demo_daily` processed data、執行 basket / signals smoke test、生成報告，並同步 Render fallback data：

```bash
python scripts/update_demo_data.py --max-points 5 --preset demo_daily --sync-demo-data
```

預設報告輸出：

- `UPDATE_REPORT.md`：建議追蹤，方便部署更新記錄。
- `data/reports/update_report.json`：本輪作為機器可讀部署報告，可追蹤；如果後續更新太頻繁，也可改為忽略。

部署資料更新完成後：

```bash
git add demo_data/processed UPDATE_REPORT.md data/reports/update_report.json
git commit -m "Update demo data"
git push origin main
```

注意：不要 commit `data/raw/` 或 `data/processed/`；只 commit `demo_data/processed` 作為線上 demo fallback data。

## 15-point coverage QA

Current demo coverage is based on the first 15 `config/collection_points.json` entries at 500m radius. The coverage workflow is read-only against processed JSONL and does not re-fetch crawler data.

Update the 15 processed points:

```bash
python scripts/update_demo_data.py --max-points 15 --preset demo_daily
```

Sync the 15-point fallback demo data when preparing deployment/demo assets:

```bash
python scripts/update_demo_data.py --max-points 15 --preset demo_daily --sync-demo-data
```

Generate the coverage report after updating processed data:

```bash
python scripts/generate_coverage_report.py --max-points 15
```

Outputs:

- `COVERAGE_REPORT.md` for human QA review.
- `data/reports/coverage_report.json` for structured QA evidence.

Do not commit `data/raw` or `data/processed`; use the report to inspect coverage quality only.

## SQLite query prototype

Import processed JSONL into the local SQLite foundation database:

```bash
python scripts/import_processed_to_sqlite.py --date latest --max-points 15
```

Inspect the SQLite store without changing API defaults:

```bash
python scripts/query_sqlite_store.py --mode health
python scripts/query_sqlite_store.py --mode candidates --point-code p001 --keyword 米
python scripts/query_sqlite_store.py --mode basket --point-code p001 --keyword 米 --keyword 洗頭水
```

This is a query-service prototype for future optional providers. Existing API routes still use the JSONL path by default.



## D2C-D4A prototypes: SQLite provider, Gemini intent, grounded answer, agent tools

### Optional SQLite provider

The default backend provider remains `jsonl`. To opt into the SQLite prototype for supported API paths only:

```powershell
$env:PROJECT2_DATA_PROVIDER="sqlite"
$env:PROJECT2_SQLITE_DB_PATH="data/app_state/project2_dev.sqlite3"
python scripts/import_processed_to_sqlite.py --date latest --max-points 15
python scripts/smoke_check_sqlite_provider.py
```

SQLite provider support is intentionally limited and prototype-only. If SQLite is enabled but the DB file is missing, the API returns a clear 503 instead of silently falling back.

### Gemini intent parser prototype

Gemini is only used to extract structured intent JSON. It must not generate prices, stores, totals, or product availability. Without `GEMINI_API_KEY`, the parser falls back to deterministic rules:

```bash
python scripts/parse_intent.py --no-gemini --text "??????????????????????"
```

### Grounded SQLite answer prototype

Grounded answers are formatted from SQLite query results; facts come from the database, not from Gemini:

```bash
python scripts/run_grounded_sqlite_answer.py --text "??????????????????????" --point-code p001
```

### Agent tool demo prototype

Agent tools expose deterministic tool functions for future integration. This is not an autonomous agent loop and does not use LLM tool selection:

```bash
python scripts/run_agent_tool_demo.py --text "??????????????????????" --provider sqlite --point-code p001
```

No RAG is used in these prototypes.

## Simple mode / advanced mode

The web demo now defaults to **簡單模式** for ordinary users who only want to know where to buy:

1. Choose a district.
2. Enter a shopping list.
3. Click `幫我找最抵買法`.

Simple mode uses larger cards, clearer result wording, optional product specification, and hides technical terms such as `product_oid`, raw ranking details, server/local mode, and alert internals.

**進階模式** keeps the full MVP surface for demos and QA:

- Direct plan generation.
- Product specification / candidate selection.
- Detailed price-gap and historical signals.
- Watchlist and Alert Center.
- Feedback.
- Server/local mode and technical diagnostics.
