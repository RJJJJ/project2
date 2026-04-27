# User Testing Guide

## 1. 試用目標

讓小範圍真實用戶試用澳門採購決策 Agent MVP，觀察他們是否能理解：

- 如何輸入購物清單
- 如何閱讀推薦方案
- 如何使用商品規格確認
- Watchlist / 關注商品是否有用
- Alert Rules 提醒候選是否容易理解

## 2. Live Web Demo URL

https://project2-three-rho.vercel.app

## 3. 建議測試流程

1. 選地區。
2. 使用頁面上的 demo example / 快速測試按鈕。
3. 點「直接生成方案」。
4. 點「先選商品規格」，比較與直接生成的差異。
5. 在候選商品卡加入關注商品。
6. 在「我的關注」更新關注商品訊號。
7. 點「檢查關注提醒」。
8. 在頁面底部填寫「試用回饋」。
9. 下載 feedback JSON 交給維護者。

## 4. 觀察問題

- 用戶輸入了什麼商品？
- 是否看得懂推薦原因？
- 是否理解「系統推薦」與「快速最低價匹配」？
- 是否覺得結果太長？
- 是否覺得 watchlist 有用？
- 是否知道價格只供參考？
- 遇到錯誤時，是否能理解友好錯誤文案與「技術詳情」？

## 5. 回饋收集方式

Web 內建 feedback 只保存在使用者當前瀏覽器：

- localStorage key: `macau-shopping-feedback-v1`
- 可在頁面按「查看已保存回饋」
- 可按「下載回饋 JSON」匯出
- 可按「清空回饋」刪除本機回饋

## 6. 限制

- 價格只供參考，以店內標示為準。
- 目前只支援 demo points。
- 無登入、無跨裝置同步。
- Watchlist 與 feedback 都只存在 browser localStorage。
- Render 免費服務可能冷啟動，第一次載入可能較慢。
- Alert Rules 只生成提醒候選，不做真正推送。
