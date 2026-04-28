# Weekly Demo Data Update Report

- Generated at: 2026-04-28T11:04:10+08:00
- Update date: 2026-04-28
- Preset: demo_daily
- Max points: 15
- Sync demo_data: true

## Point Results

| point_code | name | district | supermarkets | products | price_records | fetch_ok | validation_ok | basket_ok | signals_ok | historical_ok | historical_count | alerts_ok | alerts_count | notify_count | errors |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| p001 | 高士德 | 澳門半島 | 11 | 160 | 1535 | true | true | true | true | true | 10 | true | 1 | 1 |  |
| p002 | 義字街 | 澳門半島 | 23 | 160 | 3005 | true | true | true | true | true | 10 | true | 1 | 1 |  |
| p003 | 關閘 | 澳門半島 | 10 | 160 | 1293 | true | true | true | true | true | 10 | true | 1 | 1 |  |
| p004 | 湖畔 | 氹仔 | 4 | 160 | 541 | true | true | true | true | true | 10 | true | 1 | 1 |  |
| p005 | 海洋 | 氹仔 | 1 | 160 | 124 | true | true | true | true | true | 10 | true | 1 | 1 |  |
| p006 | 凱泉灣 | 澳門半島 | 7 | 160 | 852 | true | true | true | true | true | 0 | true | 0 | 0 |  |
| p007 | 蓮峰 | 澳門半島 | 16 | 160 | 1921 | true | true | true | true | true | 0 | true | 0 | 0 |  |
| p008 | 台山 | 澳門半島 | 14 | 160 | 1838 | true | true | true | true | true | 0 | true | 0 | 0 |  |
| p009 | 荷蘭園 | 澳門半島 | 12 | 160 | 1457 | true | true | true | true | true | 0 | true | 0 | 0 |  |
| p010 | 西灣 | 澳門半島 | 9 | 160 | 1131 | true | true | true | true | true | 0 | true | 0 | 0 |  |
| p011 | 新口岸 | 澳門半島 | 5 | 160 | 690 | true | true | true | true | true | 0 | true | 0 | 0 |  |
| p012 | 宋玉生廣場 | 澳門半島 | 4 | 160 | 565 | true | true | true | true | true | 0 | true | 0 | 0 |  |
| p013 | 觀音堂 | 澳門半島 | 11 | 160 | 1395 | true | true | true | true | true | 0 | true | 0 | 0 |  |
| p014 | 鏡湖醫院 | 澳門半島 | 16 | 160 | 1837 | true | true | true | true | true | 0 | true | 0 | 0 |  |
| p015 | 中央公園 | 氹仔 | 7 | 160 | 838 | true | true | true | true | true | 0 | true | 0 | 0 |  |

## Failed Points

- None

## Next Steps

- If any point failed, inspect `errors` and rerun the update for the same date after fixing the cause.
- For deployment fallback data, rerun with `--sync-demo-data` and commit `demo_data/processed` plus this report.
- Do not commit `data/raw` or `data/processed`.
- After updating 15-point data, run `python scripts/generate_coverage_report.py --max-points 15` to inspect coverage quality.
