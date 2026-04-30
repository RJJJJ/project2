# Catalog Confusion Audit Summary

- generated_at: 2026-04-30T13:27:07.920512+00:00
- products_total: 600
- terms_total: 18
- high_risk_occurrence_count: 133
- manual_review_count: 1
- adversarial_cases_total: 54

## Top risky terms
- 米: occurrences=79, high_risk=14, manual_review=0, risk_score=172
- 油: occurrences=99, high_risk=24, manual_review=0, risk_score=92
- 麵: occurrences=46, high_risk=0, manual_review=0, risk_score=92
- 粉: occurrences=36, high_risk=18, manual_review=0, risk_score=90
- 水: occurrences=31, high_risk=23, manual_review=0, risk_score=85
- 奶: occurrences=31, high_risk=13, manual_review=0, risk_score=75
- 紙: occurrences=30, high_risk=14, manual_review=0, risk_score=74
- 醬: occurrences=23, high_risk=11, manual_review=0, risk_score=57
- 飲品: occurrences=19, high_risk=0, manual_review=0, risk_score=38
- 糖: occurrences=10, high_risk=6, manual_review=1, risk_score=23

## High risk products
- [糖] Eclipse易極薄荷糖 (藍色) (different_category; exclude)
- [糖] 爽浪 - 超涼薄荷無糖香口珠袋裝 (attribute_only; exclude)
- [糖] 爽浪 - 無糖超涼糖 - 超涼薄荷味 (attribute_only; exclude)
- [糖] 利口樂 - 香草潤喉糖 - 檸檬味 (different_category; exclude)
- [糖] 雀巢能得利黑加侖子軟糖 (different_category; exclude)
- [油] 麗仕 精油香芬沐浴露(浪漫怡香) (different_category; exclude)
- [油] 出前一丁麻油味即食麵(袋裝) (flavor_only; exclude)
- [油] 出前一丁麻油味即食麵(碗麵) (flavor_only; exclude)
- [油] 公仔麵-麻油味(5包裝) (flavor_only; exclude)
- [油] 公仔碗麵 –麻油上素味 (different_category; exclude)
- [米] 媽媽快熟清湯米粉 (different_category; exclude)
- [米] 家樂氏原味玉米片 (different_category; exclude)
- [米] 公仔米粉 - 雪菜 (different_category; exclude)
- [米] 天鵝牌-星洲炒米粉 (different_category; exclude)
- [米] 家樂氏蜂蜜玉米片 (different_category; exclude)
- [奶] 維他奶麥精豆奶 (ambiguous; clarify)
- [奶] 維他奶低糖豆奶 (ambiguous; clarify)
- [奶] 伯朗奶茶香濃原味 (ambiguous; clarify)
- [奶] Lipton立頓金裝倍醇奶茶 (ambiguous; clarify)
- [奶] 雀巢鷹嘜煉奶(罐裝) (ambiguous; clarify)
- [水] 李施德林漱口水-原味 (different_category; exclude)
- [水] 高露潔貝齒特涼薄荷漱口水 (different_category; exclude)
- [水] 棕欖 美之選輕爽水潤洗髮乳 (ambiguous; clarify)
- [水] 麗仕 水潤柔嫩香皂 (ambiguous; clarify)
- [水] NONIO 無口氣漱口水 (清涼薄荷味) (different_category; exclude)
- [蛋] 卡夫蛋黃醬(白汁) (product_type_modifier; exclude)
- [蛋] 壽桃牌全蛋麵 (product_type_modifier; exclude)
- [蛋] 麥老大雞蛋幼面 (product_type_modifier; exclude)
- [蛋] 壽桃牌特級全蛋麵(桶裝) (product_type_modifier; exclude)
- [雞蛋] 麥老大雞蛋幼面 (product_type_modifier; exclude)
- [紙] 絲潔萬用紙 (ambiguous; clarify)
- [紙] 潔柔布藝(圓點)240抽抽取式紙面巾 (ambiguous; clarify)
- [紙] 唯潔雅廚房萬用紙 (ambiguous; clarify)
- [紙] 絲潔萬用紙 (ambiguous; clarify)
- [紙] 金樹抺手紙 (ambiguous; clarify)
- [紙巾] 好奇天然加厚嬰兒濕紙巾(補充裝) (different_category; exclude)
- [紙巾] 滴露萬用消毒濕紙巾 (different_category; exclude)
- [紙巾] 高樂氏家居消毒濕紙巾-清新香味 (different_category; exclude)
- [朱古力] 吉百利朱古力飲品 (ambiguous; clarify)
- [朱古力] 維他朱古力牛奶飲品 (ambiguous; clarify)
- [醬] 卡夫奇妙醬 (ambiguous; clarify)
- [醬] 卡夫奇妙醬 (ambiguous; clarify)
- [醬] 頂好牌千島醬 (ambiguous; clarify)
- [醬] Nutella能多益榛子醬(350g裝) (ambiguous; clarify)
- [醬] 卡夫蛋黃醬(白汁) (ambiguous; clarify)
- [粉] 媽媽快熟清湯米粉 (different_category; exclude)
- [粉] 公仔米粉 - 雪菜 (different_category; exclude)
- [粉] 天鵝牌-星洲炒米粉 (different_category; exclude)
- [粉] 米蘭麗莎墨魚汁扁意粉 (different_category; exclude)
- [粉] 塔牌龍口粉絲 (different_category; exclude)

## Suggested regression additions
- confusion_sugar_generic_001: query=糖 (manual=False, type=generic_term_guardrail)
- confusion_sugar_direct_001: query=Eclipse易極薄荷糖 (藍色) (manual=True, type=exact_product_guardrail)
- confusion_sugar_direct_002: query=利口樂 - 香草潤喉糖 - 檸檬味 (manual=True, type=exact_product_guardrail)
- confusion_sugar_direct_003: query=二寶 - 果汁糖條裝 (manual=True, type=exact_product_guardrail)
- confusion_oil_generic_001: query=油 (manual=False, type=generic_term_guardrail)
- confusion_oil_direct_001: query=麗仕 精油香芬沐浴露(浪漫怡香) (manual=True, type=exact_product_guardrail)
- confusion_oil_direct_002: query=出前一丁麻油味即食麵(袋裝) (manual=True, type=exact_product_guardrail)
- confusion_oil_direct_003: query=出前一丁麻油味即食麵(碗麵) (manual=True, type=exact_product_guardrail)
- confusion_rice_generic_001: query=米 (manual=False, type=generic_term_guardrail)
- confusion_rice_direct_001: query=京城牌拍拖米 (manual=True, type=exact_product_guardrail)
- confusion_rice_direct_002: query=好米食代台南十一號 (manual=True, type=exact_product_guardrail)
- confusion_rice_direct_003: query=媽媽快熟清湯米粉 (manual=True, type=exact_product_guardrail)
- confusion_noodle_direct_001: query=福字上湯伊麵 (manual=True, type=exact_product_guardrail)
- confusion_noodle_direct_002: query=康師傅紅燒牛肉麵 (manual=True, type=exact_product_guardrail)
- confusion_noodle_direct_003: query=天使牌瑤柱麵 (manual=True, type=exact_product_guardrail)
- confusion_noodle_simplified_direct_001: query=高潔絲親膚棉面超薄護翼衛生巾-日用21cm (manual=True, type=exact_product_guardrail)
- confusion_noodle_simplified_direct_002: query=潔柔布藝(圓點)240抽抽取式紙面巾 (manual=True, type=exact_product_guardrail)
- confusion_noodle_simplified_direct_003: query=維達金裝至尊3層盒裝面紙80抽x5盒 (manual=True, type=exact_product_guardrail)
- confusion_milk_direct_001: query=太平奶鹽梳打餅乾 (manual=True, type=exact_product_guardrail)
- confusion_milk_direct_002: query=欣得食品奶香饅頭 (manual=True, type=exact_product_guardrail)

## Terms needing manual review
- 糖
