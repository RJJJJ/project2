# MVP Roadmap

## Completed in MVP / v0.6

- Product Candidate UX：支援「先選商品規格」、常見規格推薦與不指定 product_oid fallback。
- Historical Signals：根據 processed historical data 產生歷史抵買訊號。
- Watchlist v0：Web Demo 使用 localStorage 收藏商品。
- Alert Rules v0：根據關注商品與 price signals 生成提醒候選，不做真正推送。
- Weekly Demo Data Update：demo data update workflow 與 update report smoke test。
- Deployment Demo：Vercel web demo、Render API docs 與部署後 smoke check。
- Server-side watchlist prototype：以 JSON file + user_token 原型支援跨裝置 / App / 推送前置測試。

## Next

- Notification Delivery v0：把 alert candidates 接到 Telegram / email / web notification 等真正推送渠道。
- 15 collection points：擴展 demo data 與驗收至 15 個採集點。
- Server-side watchlist / user account：支援跨裝置同步、登入與 server-side watchlist。
- Mobile app prototype：針對手機購物場景設計更輕量的 prototype。
- Persistent DB：把 JSON prototype 遷移至 PostgreSQL / Supabase / Firebase。
- Real auth：加入正式登入、session / token lifecycle 與權限模型。
- Mobile push / WeChat official account feasibility：評估真正提醒投遞渠道。

## Later milestones

- Broader product alias coverage.
- More collection-point and neighborhood scenarios.
- Route-aware or distance-aware recommendation improvements.
- User feedback capture for incorrect matches or recommendations.
- Database-backed historical price storage when MVP JSONL limits are reached.
