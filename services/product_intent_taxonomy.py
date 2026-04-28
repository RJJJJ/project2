from __future__ import annotations

from typing import Any


PRODUCT_INTENTS: dict[str, dict[str, Any]] = {
    "rice": {
        "display_name_zh": "米",
        "positive_terms": ["香米", "珍珠米", "絲苗", "糙米", "糯米", "茉莉香米", "拍拖米"],
        "negative_terms": ["米粉", "米線", "排粉", "玉米", "米糠油", "米漿", "米餅"],
        "category_allowlist": [1],
        "should_clarify": False,
    },
    "rice_noodle": {
        "display_name_zh": "米粉 / 米線",
        "positive_terms": ["米粉", "米線", "排粉"],
        "negative_terms": ["香米", "珍珠米", "糯米", "糙米"],
        "category_allowlist": [2],
        "should_clarify": False,
    },
    "instant_noodle": {
        "display_name_zh": "即食麵 / 杯麵",
        "positive_terms": ["即食麵", "杯麵", "碗麵", "公仔麵", "出前一丁", "康師傅", "辛拉麵", "拉麵"],
        "negative_terms": ["意大利麵", "意大利粉", "通心粉", "上海麵", "全蛋麵", "蝦子麵"],
        "category_allowlist": [2],
        "should_clarify": False,
    },
    "dry_noodle": {
        "display_name_zh": "乾麵 / 麵條",
        "positive_terms": ["上海麵", "全蛋麵", "蝦子麵", "麵條", "幼麵", "乾麵"],
        "negative_terms": ["即食麵", "杯麵", "米粉", "米線"],
        "category_allowlist": [2],
        "should_clarify": False,
    },
    "pasta": {
        "display_name_zh": "意粉 / 意大利麵",
        "positive_terms": ["意大利粉", "意大利麵", "通心粉", "Spaghetti", "扁意粉"],
        "negative_terms": ["即食麵", "杯麵", "碗麵"],
        "category_allowlist": [2],
        "should_clarify": False,
    },
    "cooking_oil": {
        "display_name_zh": "煮食油",
        "positive_terms": ["花生油", "粟米油", "芥花籽油", "橄欖油", "稻米油", "米糠油", "調和油", "食油", "生油"],
        "negative_terms": ["麻油味", "蠔油", "油咖喱", "油浸", "潤膚油", "護髮油", "嬰兒潤膚油", "辣椒油"],
        "category_allowlist": [3],
        "should_clarify": False,
    },
    "seasoning_oil": {
        "display_name_zh": "調味油",
        "positive_terms": ["芝麻油", "麻油", "辣椒油"],
        "negative_terms": ["麻油味即食麵", "麻油味", "蠔油"],
        "category_allowlist": [5, 18],
        "should_clarify": False,
    },
    "cooking_sugar": {
        "display_name_zh": "煮食糖",
        "positive_terms": ["砂糖", "白砂糖", "冰糖", "黃糖", "片糖"],
        "negative_terms": ["低糖", "無糖", "糖果", "薄荷糖", "潤喉糖", "香口珠", "軟糖", "蜜糖"],
        "category_allowlist": [5],
        "should_clarify": False,
    },
    "candy": {
        "display_name_zh": "糖果",
        "positive_terms": ["薄荷糖", "潤喉糖", "果汁糖", "軟糖", "香口珠"],
        "negative_terms": ["砂糖", "低糖", "無糖", "蜜糖脆皮腸"],
        "category_allowlist": [11],
        "should_clarify": False,
    },
    "chocolate_snack": {
        "display_name_zh": "朱古力零食",
        "positive_terms": ["朱古力熊仔餅", "朱古力餅", "朱古力糖", "榛子可可醬", "朱古力"],
        "negative_terms": ["朱古力飲品", "朱古力牛奶飲品", "燕麥飲品"],
        "category_allowlist": [11, 18],
        "should_clarify": False,
    },
    "chocolate_drink": {
        "display_name_zh": "朱古力飲品",
        "positive_terms": ["朱古力飲品", "朱古力牛奶飲品", "朱古力味", "可可"],
        "negative_terms": ["朱古力熊仔餅", "榛子可可醬", "朱古力餅"],
        "category_allowlist": [6, 7],
        "should_clarify": False,
    },
    "milk": {
        "display_name_zh": "牛奶",
        "positive_terms": ["牛奶", "鮮奶", "全脂奶", "低脂奶", "脫脂奶"],
        "negative_terms": ["豆奶", "奶粉", "煉奶", "奶茶", "乳酪"],
        "category_allowlist": [7],
        "should_clarify": False,
    },
    "soy_milk": {
        "display_name_zh": "豆奶",
        "positive_terms": ["豆奶", "豆乳"],
        "negative_terms": ["牛奶", "奶粉"],
        "category_allowlist": [6, 7],
        "should_clarify": False,
    },
    "soft_drink": {
        "display_name_zh": "汽水 / 飲品",
        "positive_terms": ["汽水", "飲品", "梳打"],
        "negative_terms": ["洗衣液", "洗髮"],
        "category_allowlist": [6],
        "should_clarify": True,
    },
    "cola": {
        "display_name_zh": "可樂",
        "positive_terms": ["可樂", "可口可樂"],
        "negative_terms": [],
        "category_allowlist": [6],
        "should_clarify": False,
    },
    "tissue": {
        "display_name_zh": "紙巾 / 衛生紙",
        "positive_terms": ["紙巾", "衛生紙", "面紙", "卷紙", "紙手巾", "迷你紙巾", "盒裝紙巾"],
        "negative_terms": ["濕紙巾", "消毒濕紙巾", "濕廁紙", "紙尿片"],
        "category_allowlist": [15],
        "should_clarify": False,
    },
    "wet_wipe": {
        "display_name_zh": "濕紙巾",
        "positive_terms": ["濕紙巾", "消毒濕巾", "消毒濕紙巾", "濕廁紙"],
        "negative_terms": ["衛生紙", "卷紙", "盒裝紙巾", "紙尿片"],
        "category_allowlist": [8, 9],
        "should_clarify": False,
    },
    "shampoo": {
        "display_name_zh": "洗頭水",
        "positive_terms": ["洗髮乳", "洗髮露", "洗髮", "洗頭水", "洗髮水"],
        "negative_terms": ["沐浴露", "香皂", "潔膚"],
        "category_allowlist": [10],
        "should_clarify": False,
    },
    "laundry_detergent": {
        "display_name_zh": "洗衣用品",
        "positive_terms": ["洗衣液", "洗衣粉", "洗衣膠囊", "洗衣"],
        "negative_terms": ["洗潔精", "洗手液", "洗髮"],
        "category_allowlist": [9],
        "should_clarify": False,
    },
    "toothpaste": {
        "display_name_zh": "牙膏",
        "positive_terms": ["牙膏"],
        "negative_terms": ["漱口水"],
        "category_allowlist": [10],
        "should_clarify": False,
    },
    "mouthwash": {
        "display_name_zh": "漱口水",
        "positive_terms": ["漱口水"],
        "negative_terms": ["牙膏"],
        "category_allowlist": [10],
        "should_clarify": False,
    },
    "chips": {
        "display_name_zh": "薯片",
        "positive_terms": ["薯片", "品客", "卡樂B", "珍珍", "威士"],
        "negative_terms": ["薯條"],
        "category_allowlist": [11],
        "should_clarify": False,
    },
    "fries": {
        "display_name_zh": "薯條",
        "positive_terms": ["薯條"],
        "negative_terms": [],
        "category_allowlist": [],
        "should_clarify": False,
    },
    "egg": {
        "display_name_zh": "雞蛋",
        "positive_terms": ["雞蛋", "鮮蛋", "蛋"],
        "negative_terms": ["雞蛋幼面", "全蛋麵", "蛋黃醬"],
        "category_allowlist": [],
        "should_clarify": False,
    },
    "unknown_or_not_covered": {
        "display_name_zh": "未知或未收錄",
        "positive_terms": [],
        "negative_terms": [],
        "category_allowlist": [],
        "should_clarify": True,
    },
}


AMBIGUOUS_QUERIES: dict[str, list[str]] = {
    "糖": ["cooking_sugar", "candy"],
    "油": ["cooking_oil", "seasoning_oil"],
    "朱古力": ["chocolate_drink", "chocolate_snack"],
    "紙巾": ["tissue", "wet_wipe"],
    "麵": ["instant_noodle", "pasta", "dry_noodle"],
    "面": ["instant_noodle", "pasta", "dry_noodle"],
    "米": ["rice", "rice_noodle"],
    "奶": ["milk", "soy_milk"],
}


QUERY_SYNONYMS: dict[str, str] = {
    "洗頭水": "shampoo",
    "洗髮水": "shampoo",
    "洗髮乳": "shampoo",
    "洗髮露": "shampoo",
    "食油": "cooking_oil",
    "煮食油": "cooking_oil",
    "生油": "cooking_oil",
    "砂糖": "cooking_sugar",
    "白砂糖": "cooking_sugar",
    "可樂": "cola",
    "汽水": "soft_drink",
    "米粉": "rice_noodle",
    "即食麵": "instant_noodle",
    "薯片": "chips",
    "牙膏": "toothpaste",
    "洗衣液": "laundry_detergent",
    "朱古力飲品": "chocolate_drink",
    "濕紙巾": "wet_wipe",
}


NOT_COVERED_QUERIES = {"M&M", "m&m", "MM", "薯條", "雞蛋", "鮮蛋"}
