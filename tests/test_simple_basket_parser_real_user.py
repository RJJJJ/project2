from services.simple_basket_parser import parse_simple_basket_text


def by_keyword(items):
    return {item["keyword"]: item for item in items}


def test_space_separated_real_user_list():
    items = by_keyword(parse_simple_basket_text("兩包麵 一包薯條 四包薯片 油 糖 M&M"))
    assert items["麵"]["quantity"] == 2
    assert items["麵"]["unit"] == "包"
    assert items["薯條"]["quantity"] == 1
    assert items["薯片"]["quantity"] == 4
    assert items["油"]["quantity"] == 1
    assert items["糖"]["quantity"] == 1
    assert items["M&M"]["quantity"] == 1


def test_punctuation_and_newline_separators():
    for text in ["米、洗頭水、紙巾", "米，洗頭水，紙巾", "米, 洗頭水, 紙巾", "米\n洗頭水\n紙巾"]:
        assert [item["keyword"] for item in parse_simple_basket_text(text)] == ["米", "洗頭水", "紙巾"]


def test_natural_sentences():
    assert by_keyword(parse_simple_basket_text("我想買一包米、兩支洗頭水、一包紙巾"))["洗頭水"]["quantity"] == 2
    assert by_keyword(parse_simple_basket_text("幫我搵兩包麵同四包薯片"))["薯片"]["quantity"] == 4
    assert [item["keyword"] for item in parse_simple_basket_text("我喺高士德想買米、油、糖")] == ["米", "油", "糖"]


def test_digits_without_and_with_units():
    assert by_keyword(parse_simple_basket_text("2 麵 4 薯片 1 食油"))["麵"]["quantity"] == 2
    parsed = by_keyword(parse_simple_basket_text("2包麵 4包薯片 1支油"))
    assert parsed["薯片"]["quantity"] == 4
    assert parsed["油"]["unit"] == "支"


def test_english_symbol_brands_are_preserved():
    keys = [item["keyword"] for item in parse_simple_basket_text("M&M m&m M and M Coca Cola OREO Oreo KitKat Tempo C&S")]
    assert "M&M" in keys
    assert "Coca Cola" in keys
    assert "C&S" in keys


def test_duplicate_items_merge():
    items = by_keyword(parse_simple_basket_text("米 一包米 兩包米"))
    assert items["米"]["quantity"] == 4


def test_empty_and_garbage_do_not_crash():
    assert parse_simple_basket_text("") == []
    assert parse_simple_basket_text("???") == []
    assert parse_simple_basket_text("幫我買東西") == []
