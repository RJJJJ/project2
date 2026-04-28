# 多地區 MVP 驗收報告

- 生成時間：2026-04-28T11:26:21
- 測試句子：我想買一包米、兩支洗頭水、一包紙巾

## 每個 point 的結果

| point_code | name | district | has_processed_data | basket_ok | basket_total | recommended_plan_type | signals_ok | largest_gap_count | warnings | errors |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| p001 | 高士德 | 澳門半島 | True | True | 12.0 | cheapest_by_item | True | 2 |  |  |

## Failed Points

- 無

## 下一步建議

- 若有 point 缺少 processed data，先執行：`python scripts/fetch_demo_points.py --max-points 5 --preset demo_daily`
- 若 basket pipeline 失敗，檢查該 point 的商品價格 JSONL 是否包含測試句子的商品關鍵字。
- 若 signals 失敗，檢查該 point 是否有至少一個 `category_*_prices.jsonl` 檔案且 JSONL 格式有效。
