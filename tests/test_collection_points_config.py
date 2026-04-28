from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "collection_points.json"
VALID_DISTRICTS = {"\u6fb3\u9580\u534a\u5cf6", "\u6c39\u4ed4", "\u8def\u74b0", "\u6fb3\u5927"}


def _load_points(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_active_config_contains_at_least_15_points() -> None:
    points = _load_points(CONFIG_PATH)

    assert len(points) >= 15


def test_active_point_codes_are_unique() -> None:
    points = _load_points(CONFIG_PATH)
    point_codes = [point["point_code"] for point in points]

    assert len(point_codes) == len(set(point_codes))


def test_active_points_have_valid_districts() -> None:
    points = _load_points(CONFIG_PATH)

    for point in points:
        assert point.get("district") in VALID_DISTRICTS


def test_active_points_have_required_500m_coordinates() -> None:
    points = _load_points(CONFIG_PATH)

    for point in points:
        assert point.get("lat") is not None
        assert point.get("lng") is not None
        assert point.get("dst") is not None
        assert point["dst"] == 500
