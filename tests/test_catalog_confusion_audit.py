from __future__ import annotations

import json
import sys
from pathlib import Path

from scripts import run_catalog_confusion_audit
from services.catalog_confusion_audit import classify_term_occurrence


def _product(name: str, category_id: int = 1, category_name: str = "測試", oid: str | None = None) -> dict:
    return {
        "product_oid": oid or name,
        "product_name": name,
        "category_id": category_id,
        "category_name": category_name,
        "package_quantity": "",
    }


def test_classify_sugar_examples():
    true_product = classify_term_occurrence("糖", _product("太古純正砂糖", 5, "調味品"))
    assert true_product["occurrence_type"] == "true_product"
    assert true_product["suggested_guardrail"] == "allow"

    attribute_only = classify_term_occurrence("糖", _product("維他奶低糖豆奶", 7, "飲品"))
    assert attribute_only["occurrence_type"] == "attribute_only"
    assert attribute_only["suggested_guardrail"] == "exclude"

    candy = classify_term_occurrence("糖", _product("無糖香口珠", 11, "零食"))
    assert candy["occurrence_type"] in {"attribute_only", "different_category"}
    assert candy["suggested_guardrail"] in {"exclude", "review"}


def test_classify_oil_egg_and_rice_examples():
    cooking_oil = classify_term_occurrence("油", _product("獅球嘜花生油", 3, "食油"))
    assert cooking_oil["occurrence_type"] == "true_product"

    flavor_noodle = classify_term_occurrence("油", _product("出前一丁麻油味即食麵", 2, "即食麵"))
    assert flavor_noodle["occurrence_type"] == "flavor_only"
    assert flavor_noodle["suggested_guardrail"] == "exclude"

    oyster_sauce = classify_term_occurrence("油", _product("李錦記蠔油", 5, "調味品"))
    assert oyster_sauce["occurrence_type"] == "different_category"

    egg_noodle = classify_term_occurrence("雞蛋", _product("麥老大雞蛋幼面", 2, "麵類"))
    assert egg_noodle["occurrence_type"] == "product_type_modifier"

    rice = classify_term_occurrence("米", _product("金象絲苗米", 1, "米"))
    assert rice["occurrence_type"] == "true_product"

    rice_noodle = classify_term_occurrence("米", _product("東莞米粉", 2, "麵類"))
    assert rice_noodle["occurrence_type"] == "different_category"

    rice_bran_oil = classify_term_occurrence("米", _product("健康米糠油", 3, "食油"))
    assert rice_bran_oil["occurrence_type"] == "different_category"


def test_audit_script_runs_on_fake_catalog_without_crash(tmp_path, monkeypatch):
    fake_products = [
        _product("太古純正砂糖", 5, "調味品"),
        _product("維他奶低糖豆奶", 7, "飲品"),
        _product("出前一丁麻油味即食麵", 2, "即食麵"),
        _product("麥老大雞蛋幼面", 2, "麵類"),
    ]
    monkeypatch.setattr(run_catalog_confusion_audit, "load_catalog_for_confusion_audit", lambda db_path: fake_products)
    output_dir = tmp_path / "eval"
    argv = [
        "run_catalog_confusion_audit.py",
        "--db-path",
        "fake.sqlite3",
        "--output-dir",
        str(output_dir),
        "--generate-adversarial-cases",
    ]
    monkeypatch.setattr(sys, "argv", argv)
    assert run_catalog_confusion_audit.main() == 0
    audit_path = output_dir / "catalog_confusion_audit.json"
    summary_path = output_dir / "catalog_confusion_audit_summary.md"
    adversarial_path = output_dir / "catalog_adversarial_cases.json"
    assert audit_path.exists()
    assert summary_path.exists()
    assert adversarial_path.exists()
    payload = json.loads(audit_path.read_text(encoding="utf-8"))
    assert payload["products_total"] == len(fake_products)
    assert "糖" in payload["terms"]
