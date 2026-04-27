# 部署前整理筆記

## 本地部署架構

- Backend：FastAPI，入口為 `app.main:app`，本地啟動命令為 `python scripts/run_api.py`
- Frontend：Vue 3 + Vite + Tailwind CSS，位於 `frontend/`
- Telegram Bot：沿用現有 bot 入口與 `.env` 內的 `TELEGRAM_BOT_TOKEN`
- Data：目前使用 `data/processed/{date}/{point_code}/` 下的 JSONL 檔案

## 未來部署建議

- Backend：Render / Railway / VPS
- Frontend：Vercel / Netlify
- Data：短期沿用 processed JSONL；後續若需要多人使用、歷史查詢或管理後台，可遷移 PostgreSQL

## Git 資料限制

不要把以下資料 commit 到 Git：

- `data/raw/`
- `data/processed/`
- 真實 `.env`

只提交 `.env.example` 作為設定範本。

## API Base URL

前端預設 API URL：

```text
http://127.0.0.1:8000
```

本地開發可在 `frontend` 目錄用環境變數覆蓋：

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

部署到 Vercel / Netlify 時，請在平台環境變數設定：

```text
VITE_API_BASE_URL=https://your-backend.example.com
```

## Backend on Render

1. New Web Service
2. Connect GitHub repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Environment variables:

```text
PROCESSED_ROOT=demo_data/processed
ALLOWED_ORIGINS=https://your-vercel-app.vercel.app
```

`PROCESSED_ROOT` 也可以不填；若 `data/processed` 不存在或沒有資料，API 會 fallback 到 `demo_data/processed`。

## Frontend on Vercel

1. Import `frontend` directory
2. Framework: Vite
3. Build command: `npm run build`
4. Output directory: `dist`
5. Env:

```text
VITE_API_BASE_URL=https://your-backend-url
```

## 更新線上 Demo Data

- `demo_data/processed` 是 Render fallback data；Render 上的 `PROCESSED_ROOT=demo_data/processed` 會讀取這份已提交資料。
- 更新流程：

```bash
python scripts/update_demo_data.py --max-points 5 --preset demo_daily --sync-demo-data
git add demo_data/processed UPDATE_REPORT.md data/reports/update_report.json
git commit -m "Update demo data"
git push origin main
```

- `scripts/update_demo_data.py` 會先更新 `data/processed/{date}`，再驗證 processed data、basket pipeline 與 price signals，生成 `UPDATE_REPORT.md` 與 `data/reports/update_report.json`。
- 使用 `--sync-demo-data` 時，script 只會把最新 processed date 的前 5 個 point 複製到 `demo_data/processed/{date}/{point_code}`；不會複製 raw data。
- 請勿 commit `data/raw/` 或 `data/processed/`。
- commit `demo_data/processed` 並 push 後，Render 會按 repo 更新重新部署，線上 demo fallback data 也會更新。
