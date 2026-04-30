from __future__ import annotations

from services.catalog_confusion_audit import audit_confusion_terms, generate_adversarial_cases_from_audit


def _product(name: str, category_id: int = 1, category_name: str = "測試") -> dict:
    return {
        "product_oid": name,
        "product_name": name,
        "category_id": category_id,
        "category_name": category_name,
        "package_quantity": "",
    }


def test_generate_adversarial_cases_covers_sugar_oil_and_egg():
    products = [
        _product("太古純正砂糖", 5, "調味品"),
        _product("維他奶低糖豆奶", 7, "飲品"),
        _product("出前一丁麻油味即食麵(袋裝)", 2, "即食麵"),
        _product("油浸吞拿魚", 12, "罐頭"),
        _product("李錦記蠔油", 5, "調味品"),
        _product("麥老大雞蛋幼面", 2, "麵類"),
        _product("蛋黃醬", 5, "調味品"),
    ]
    audit_result = audit_confusion_terms(products, terms=["糖", "油", "雞蛋"])
    cases = generate_adversarial_cases_from_audit(audit_result)
    terms = {case["term"] for case in cases}
    assert {"糖", "油", "雞蛋"}.issubset(terms)

    oil_generic = next(case for case in cases if case["term"] == "油" and case["case_type"] == "generic_term_guardrail")
    assert oil_generic["needs_manual_label"] is False
    assert oil_generic["expected"]["must_not_include_product_names"]

    egg_generic = next(case for case in cases if case["term"] == "雞蛋" and case["case_type"] == "generic_term_guardrail")
    assert egg_generic["expected"]["status"] == "not_covered"
    assert "must_not_include_product_names" in egg_generic["expected"]

    direct_case = next(case for case in cases if case["query"] == "麥老大雞蛋幼面")
    assert direct_case["expected"]["must_include_product_names"] == ["麥老大雞蛋幼面"]
