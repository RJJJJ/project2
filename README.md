# 澳門採購決策 Agent MVP

## 啟動後端

```bash
python scripts/run_api.py
```

預設 API base URL：

```text
http://127.0.0.1:8000
```

## 啟動前端

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
