# 澳門採購決策 MVP Demo

基於澳門消委會公開物價資料的本地採購決策 MVP。

## 已完成能力

- 抓取消委會超市物價 API
- 清洗 JSONL
- 商品 alias 匹配
- 自然語言購物清單解析
- 三種採購方案
- 推薦方案選擇

## Demo 指令

```powershell
python scripts/demo.py
```

## 手動指令

```powershell
python scripts/ask_processed_basket.py --date 2026-04-25 --point-code p001 "我想買一包米、兩支洗頭水、一包紙巾" --format text
```

## 注意事項

- 價格只供參考，以店內標示為準
- 目前基於 processed JSONL，不依賴 PostgreSQL
- 目前不是全澳最低價，只是指定採集點附近資料
- 目前未加入真實地圖路線
