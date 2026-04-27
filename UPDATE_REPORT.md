# Weekly Demo Data Update Report

- Generated at: 2026-04-27T15:54:41+08:00
- Update date: 2026-04-27
- Preset: demo_daily
- Max points: 5
- Sync demo_data: true

## Point Results

| point_code | name | district | supermarkets | products | price_records | fetch_ok | validation_ok | basket_ok | signals_ok | errors |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| p001 | 高士德 | 澳門半島 | 11 | 160 | 1535 | true | true | true | true |  |
| p002 | 義字街 | 澳門半島 | 23 | 160 | 3005 | true | true | true | true |  |
| p003 | 關閘 | 澳門半島 | 10 | 160 | 1293 | true | true | true | true |  |
| p004 | 湖畔 | 氹仔 | 4 | 160 | 541 | true | true | true | true |  |
| p005 | 海洋 | 氹仔 | 1 | 160 | 124 | true | true | true | true |  |

## Failed Points

- None

## Next Steps

- If any point failed, inspect `errors` and rerun the update for the same date after fixing the cause.
- For deployment fallback data, rerun with `--sync-demo-data` and commit `demo_data/processed` plus this report.
- Do not commit `data/raw` or `data/processed`.
