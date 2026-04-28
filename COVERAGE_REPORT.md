# Data Coverage Report

- Generated at: 2026-04-28T03:41:09.176589+00:00
- Date: 2026-04-28
- Total points: 15

## Summary

- Good: 12
- Medium: 2
- Low: 1
- Needs review: 1
- District counts: {"澳門半島": 12, "氹仔": 3}

## Point table

| point_code | name | district | supermarkets | products | price_records | coverage_level | needs_review | warnings |
|---|---|---|---:|---:|---:|---|---|---|
| p001 | 高士德 | 澳門半島 | 11 | 159 | 1535 | good | False |  |
| p002 | 義字街 | 澳門半島 | 23 | 160 | 3005 | good | False |  |
| p003 | 關閘 | 澳門半島 | 10 | 159 | 1293 | good | False |  |
| p004 | 湖畔 | 氹仔 | 4 | 159 | 541 | medium | False |  |
| p005 | 海洋 | 氹仔 | 1 | 124 | 124 | low | True |  |
| p006 | 凱泉灣 | 澳門半島 | 7 | 160 | 852 | good | False |  |
| p007 | 蓮峰 | 澳門半島 | 16 | 160 | 1921 | good | False |  |
| p008 | 台山 | 澳門半島 | 14 | 159 | 1838 | good | False |  |
| p009 | 荷蘭園 | 澳門半島 | 12 | 159 | 1457 | good | False |  |
| p010 | 西灣 | 澳門半島 | 9 | 160 | 1131 | good | False |  |
| p011 | 新口岸 | 澳門半島 | 5 | 158 | 690 | good | False |  |
| p012 | 宋玉生廣場 | 澳門半島 | 4 | 158 | 565 | medium | False |  |
| p013 | 觀音堂 | 澳門半島 | 11 | 160 | 1395 | good | False |  |
| p014 | 鏡湖醫院 | 澳門半島 | 16 | 159 | 1837 | good | False |  |
| p015 | 中央公園 | 氹仔 | 7 | 160 | 838 | good | False |  |

## Low coverage points

- p005 海洋 (氹仔)

## Needs review points

- p005 海洋: low

## Next actions

- Review any low coverage or needs_review points before demo/testing.
- If coverage looks stale, run `python scripts/update_demo_data.py --max-points 15 --preset demo_daily` and regenerate this report.
- Do not expand point count or radius from this report; use it only for QA coverage visibility.
