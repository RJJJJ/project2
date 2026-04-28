from __future__ import annotations

from services.product_matching_rules import (
    candidate_text_match_score,
    expand_keyword,
    negative_terms_for_keyword,
    normalize_keyword,
    package_preference_score,
)

RICE = "\u7c73"
TISSUE = "\u7d19\u5dfe"
SHAMPOO = "\u6d17\u982d\u6c34"


def test_expand_keyword_supports_core_household_terms() -> None:
    assert "\u73cd\u73e0\u7c73" in expand_keyword(RICE)
    assert "shampoo" in expand_keyword(SHAMPOO)
    assert "\u5377\u7d19" in expand_keyword(TISSUE)


def test_negative_terms_guard_common_false_positives() -> None:
    assert "\u7c73\u7c89" in negative_terms_for_keyword(RICE)
    assert "\u6fd5\u7d19\u5dfe" in negative_terms_for_keyword(TISSUE)
    assert "\u6c90\u6d74\u9732" in negative_terms_for_keyword(SHAMPOO)


def test_rice_package_preference_penalizes_rice_noodles() -> None:
    good = candidate_text_match_score(RICE, "\u5bcc\u58eb\u73cd\u73e0\u7c73", "5\u516c\u65a4", "\u7c73\u985e")
    bad = candidate_text_match_score(RICE, "\u5abd\u5abd\u5feb\u719f\u6e05\u6e6f\u7c73\u7c89", "55\u514b", "\u7a40\u985e\u98df\u54c1")

    assert good > bad
    assert bad < 0


def test_tissue_package_preference_penalizes_wet_wipes() -> None:
    household = candidate_text_match_score(TISSUE, "Tempo \u76d2\u88dd\u7d19\u5dfe", "5\u76d2", "\u7d19\u54c1")
    wet = candidate_text_match_score(TISSUE, "\u6ef4\u9732\u842c\u7528\u6d88\u6bd2\u6fd5\u7d19\u5dfe", "80\u7247", "\u7d19\u54c1")

    assert household > wet
    assert wet < 0


def test_shampoo_expansion_scores_shampoo_above_body_wash() -> None:
    shampoo = candidate_text_match_score(SHAMPOO, "Head & Shoulders Shampoo", "750ml", "\u500b\u4eba\u8b77\u7406")
    body_wash = candidate_text_match_score(SHAMPOO, "\u67d0\u54c1\u724c\u6c90\u6d74\u9732", "1L", "\u500b\u4eba\u8b77\u7406")

    assert shampoo > body_wash
    assert body_wash < 0


def test_normalize_keyword_trims_and_casefolds() -> None:
    assert normalize_keyword(" Shampoo ") == "shampoo"
    assert package_preference_score(SHAMPOO, "\u6f58\u5a77\u6d17\u9aee\u9732", "700ml") > 0
