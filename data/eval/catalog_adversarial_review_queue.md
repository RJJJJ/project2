# Catalog Adversarial Manual Review Queue

## Summary
- total pending cases: 42
- by risk_term:
  - 奶: 3
  - 朱古力: 2
  - 水: 3
  - 油: 3
  - 米: 3
  - 粉: 3
  - 糖: 3
  - 紙: 3
  - 紙巾: 3
  - 茶: 3
  - 蛋: 1
  - 醬: 3
  - 面: 3
  - 鹽: 3
  - 麵: 3
- by suggested_guardrail:
  - exact_product_guardrail: 42
- by suggested_review_decision:
  - revise_expected: 42

## Review Instructions
- `promote_to_strict`: Promote this case into strict enforced regression coverage.
- `keep_pending`: Keep this case pending manual labeling for later review.
- `ignore_case`: Ignore this case in regression because it is not useful or not valid.
- `revise_expected`: The case is useful but expected JSON needs manual revision before promotion.
- `needs_data_check`: Catalog data or product labeling needs validation before this case can be decided.

## Pending Cases Table

| case_id | query | risk_term | related_product_names | suggested_guardrail | suggested_review_decision | review_decision |
| --- | --- | --- | --- | --- | --- | --- |
| confusion_sugar_direct_001 | Eclipse易極薄荷糖 (藍色) | 糖 | Eclipse易極薄荷糖 (藍色) | exact_product_guardrail | revise_expected |  |
| confusion_sugar_direct_002 | 利口樂 - 香草潤喉糖 - 檸檬味 | 糖 | 利口樂 - 香草潤喉糖 - 檸檬味 | exact_product_guardrail | revise_expected |  |
| confusion_sugar_direct_003 | 二寶 - 果汁糖條裝 | 糖 | 二寶 - 果汁糖條裝 | exact_product_guardrail | revise_expected |  |
| confusion_oil_direct_001 | 麗仕 精油香芬沐浴露(浪漫怡香) | 油 | 麗仕 精油香芬沐浴露(浪漫怡香) | exact_product_guardrail | revise_expected |  |
| confusion_oil_direct_002 | 出前一丁麻油味即食麵(袋裝) | 油 | 出前一丁麻油味即食麵(袋裝) | exact_product_guardrail | revise_expected |  |
| confusion_oil_direct_003 | 出前一丁麻油味即食麵(碗麵) | 油 | 出前一丁麻油味即食麵(碗麵) | exact_product_guardrail | revise_expected |  |
| confusion_rice_direct_001 | 京城牌拍拖米 | 米 | 京城牌拍拖米 | exact_product_guardrail | revise_expected |  |
| confusion_rice_direct_002 | 好米食代台南十一號 | 米 | 好米食代台南十一號 | exact_product_guardrail | revise_expected |  |
| confusion_rice_direct_003 | 媽媽快熟清湯米粉 | 米 | 媽媽快熟清湯米粉 | exact_product_guardrail | revise_expected |  |
| confusion_noodle_direct_001 | 福字上湯伊麵 | 麵 | 福字上湯伊麵 | exact_product_guardrail | revise_expected |  |
| confusion_noodle_direct_002 | 康師傅紅燒牛肉麵 | 麵 | 康師傅紅燒牛肉麵 | exact_product_guardrail | revise_expected |  |
| confusion_noodle_direct_003 | 天使牌瑤柱麵 | 麵 | 天使牌瑤柱麵 | exact_product_guardrail | revise_expected |  |
| confusion_noodle_simplified_direct_001 | 高潔絲親膚棉面超薄護翼衛生巾-日用21cm | 面 | 高潔絲親膚棉面超薄護翼衛生巾-日用21cm | exact_product_guardrail | revise_expected |  |
| confusion_noodle_simplified_direct_002 | 潔柔布藝(圓點)240抽抽取式紙面巾 | 面 | 潔柔布藝(圓點)240抽抽取式紙面巾 | exact_product_guardrail | revise_expected |  |
| confusion_noodle_simplified_direct_003 | 維達金裝至尊3層盒裝面紙80抽x5盒 | 面 | 維達金裝至尊3層盒裝面紙80抽x5盒 | exact_product_guardrail | revise_expected |  |
| confusion_milk_direct_001 | 太平奶鹽梳打餅乾 | 奶 | 太平奶鹽梳打餅乾 | exact_product_guardrail | revise_expected |  |
| confusion_milk_direct_002 | 欣得食品奶香饅頭 | 奶 | 欣得食品奶香饅頭 | exact_product_guardrail | revise_expected |  |
| confusion_milk_direct_003 | 欣得食品奶皇包 | 奶 | 欣得食品奶皇包 | exact_product_guardrail | revise_expected |  |
| confusion_water_direct_001 | 李施德林漱口水-原味 | 水 | 李施德林漱口水-原味 | exact_product_guardrail | revise_expected |  |
| confusion_water_direct_002 | 高露潔貝齒特涼薄荷漱口水 | 水 | 高露潔貝齒特涼薄荷漱口水 | exact_product_guardrail | revise_expected |  |
| confusion_water_direct_003 | 棕欖 美之選輕爽水潤洗髮乳 | 水 | 棕欖 美之選輕爽水潤洗髮乳 | exact_product_guardrail | revise_expected |  |
| confusion_egg_direct_001 | 卡夫蛋黃醬(白汁) | 蛋 | 卡夫蛋黃醬(白汁) | exact_product_guardrail | revise_expected |  |
| confusion_paper_direct_001 | 絲潔萬用紙 | 紙 | 絲潔萬用紙 | exact_product_guardrail | revise_expected |  |
| confusion_paper_direct_002 | 潔柔布藝(圓點)240抽抽取式紙面巾 | 紙 | 潔柔布藝(圓點)240抽抽取式紙面巾 | exact_product_guardrail | revise_expected |  |
| confusion_paper_direct_003 | 唯潔雅廚房萬用紙 | 紙 | 唯潔雅廚房萬用紙 | exact_product_guardrail | revise_expected |  |
| confusion_tissue_direct_001 | 好奇天然加厚嬰兒濕紙巾(補充裝) | 紙巾 | 好奇天然加厚嬰兒濕紙巾(補充裝) | exact_product_guardrail | revise_expected |  |
| confusion_tissue_direct_002 | 滴露萬用消毒濕紙巾 | 紙巾 | 滴露萬用消毒濕紙巾 | exact_product_guardrail | revise_expected |  |
| confusion_tissue_direct_003 | 高樂氏家居消毒濕紙巾-清新香味 | 紙巾 | 高樂氏家居消毒濕紙巾-清新香味 | exact_product_guardrail | revise_expected |  |
| confusion_chocolate_direct_001 | 吉百利朱古力飲品 | 朱古力 | 吉百利朱古力飲品 | exact_product_guardrail | revise_expected |  |
| confusion_chocolate_direct_002 | 維他朱古力牛奶飲品 | 朱古力 | 維他朱古力牛奶飲品 | exact_product_guardrail | revise_expected |  |
| confusion_tea_direct_001 | Lipton立頓黃色標籤茶 | 茶 | Lipton立頓黃色標籤茶 | exact_product_guardrail | revise_expected |  |
| confusion_tea_direct_002 | 川寧豪門伯爵茶 | 茶 | 川寧豪門伯爵茶 | exact_product_guardrail | revise_expected |  |
| confusion_tea_direct_003 | 王老吉涼茶(罐裝) | 茶 | 王老吉涼茶(罐裝) | exact_product_guardrail | revise_expected |  |
| confusion_salt_direct_001 | 太平奶鹽梳打餅乾 | 鹽 | 太平奶鹽梳打餅乾 | exact_product_guardrail | revise_expected |  |
| confusion_salt_direct_002 | 淘大減鹽蠔油 | 鹽 | 淘大減鹽蠔油 | exact_product_guardrail | revise_expected |  |
| confusion_salt_direct_003 | Lurpak丹麥銀寶有鹽軟牛油 | 鹽 | Lurpak丹麥銀寶有鹽軟牛油 | exact_product_guardrail | revise_expected |  |
| confusion_sauce_direct_001 | 卡夫奇妙醬 | 醬 | 卡夫奇妙醬 | exact_product_guardrail | revise_expected |  |
| confusion_sauce_direct_002 | 頂好牌千島醬 | 醬 | 頂好牌千島醬 | exact_product_guardrail | revise_expected |  |
| confusion_sauce_direct_003 | Nutella能多益榛子醬(350g裝) | 醬 | Nutella能多益榛子醬(350g裝) | exact_product_guardrail | revise_expected |  |
| confusion_powder_direct_001 | 媽媽快熟清湯米粉 | 粉 | 媽媽快熟清湯米粉 | exact_product_guardrail | revise_expected |  |
| confusion_powder_direct_002 | 百得阿姨意大利粉 Spaghetti n.5 | 粉 | 百得阿姨意大利粉 Spaghetti n.5 | exact_product_guardrail | revise_expected |  |
| confusion_powder_direct_003 | 公仔米粉 - 雪菜 | 粉 | 公仔米粉 - 雪菜 | exact_product_guardrail | revise_expected |  |
