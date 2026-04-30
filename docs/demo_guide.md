# Demo Guide

## 1. Demo goal

This demo should show that Project2 is not just a keyword search UI. It can:

- handle a clear basket request
- ask for clarification on ambiguous terms
- support brand search
- support partial product search
- return not-covered messaging safely
- reject subjective unsupported questions
- switch deterministic decision policies

## 2. Demo setup

### Backend

```powershell
.\venv\Scripts\Activate.ps1
python scripts\run_api.py
```

### Frontend

```powershell
cd frontend
npm run dev
```

### Optional API smoke test

```powershell
python scripts\run_shopping_agent.py ^
  --query "我想買砂糖同洗頭水" ^
  --db-path data\app_state\project2_dev.sqlite3 ^
  --point-code p001 ^
  --include-price-plan ^
  --retrieval-mode rag_v2 ^
  --debug-json
```

## 3. Demo query script

### A. 我想買砂糖同洗頭水

Expected:

- `basket_optimization`
- resolved `cooking_sugar` / `shampoo`
- `price_plan.status = ok`

### B. 出前一丁

Expected:

- `brand_search`
- no flavor specified
- brand candidate list / priceable brand results

### C. 出前一丁麻油味

Expected:

- `partial_product_search`
- top candidate includes `出前一丁麻油味即食麵(袋裝)`

### D. 麥老大雞蛋幼面

Expected:

- `direct_product_search`

### E. 雞蛋

Expected:

- `not_covered`
- does not match `雞蛋幼面`

### F. 糖

Expected:

- `ambiguous` / `needs_clarification`

### G. 最好吃的麵

Expected:

- subjective / unsupported
- offers supported alternatives instead of fake taste advice

### H. 兩包麵 一包薯條 四包薯片 油 糖 M&M

Expected:

- `needs_clarification`
- resolved `薯片`
- ambiguous `麵 / 油 / 糖`
- not-covered `薯條 / M&M`
- price output only for confirmed items

### I. BB用嘅濕紙巾

Expected:

- wet wipe / baby wet wipe related retrieval path

### J. 我想買食油、朱古力飲品、牙膏

Expected:

- all resolved
- `price_plan.status = ok`

## 4. Screenshots checklist

- home screen
- successful result
- needs clarification result
- not covered result
- brand search result
- subjective unsupported result
- advanced controls / debug controls

## 5. Demo talking points

- Why this is safer than keyword search:
  - generic risky terms are routed through guardrails first
- How ambiguity is handled:
  - the system asks for clarification instead of making unsafe assumptions
- Why LLM is optional:
  - core pricing and decision logic remain deterministic without Gemini / Ollama
- How quality is protected:
  - regression pack
  - catalog confusion audit
  - manual review workflow
