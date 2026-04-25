from __future__ import annotations

from services.product_aliases import expand_keyword


def test_expand_keyword_known_alias() -> None:
    aliases = expand_keyword("洗頭水")

    assert len(aliases) > 1
    assert "洗頭水" in aliases
    assert "洗髮露" in aliases
    assert "潘婷" in aliases


def test_expand_keyword_unknown_alias() -> None:
    assert expand_keyword("不存在") == ["不存在"]
