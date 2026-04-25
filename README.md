# 澳門採購決策 Agent MVP

本專案是一個本地採購決策 MVP，用 processed JSONL 價格資料，為指定採集點附近約 500 米的購物清單產生採購方案，並提供本區價差訊號。

## 目前功能

- FastAPI Backend：提供健康檢查、採集點、購物籃方案、價差訊號 API
- Vue Web Demo：選擇地區、輸入購物清單、顯示推薦方案與價差訊號
- Telegram Bot：支援 `/check`、`/signals`、`/point`
- 多地區 collection points：支援前 5 個採集點設定
- Demo data 抓取與多地區驗收工具

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
