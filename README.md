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

## Web Demo 截圖驗收 Checklist

- API 已啟動：`python scripts/run_api.py`
- 前端已啟動：`cd frontend && npm run dev`
- 地區可以載入，並預設顯示 `p001`
- 點擊「生成採購方案」後可看到推薦方案、總價、建議超市與商品明細
- 「本區價差訊號」可顯示最多 5 個價差商品卡片
