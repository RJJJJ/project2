from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "collection_points.json"
EXAMPLE_CONFIG_PATH = PROJECT_ROOT / "config" / "collection_points.example.json"


def _load_points(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_active_point_codes_are_unique() -> None:
    points = _load_points(CONFIG_PATH)
    point_codes = [point["point_code"] for point in points]

    assert len(point_codes) == len(set(point_codes))


def test_active_points_have_usable_coordinates() -> None:
    points = _load_points(CONFIG_PATH)

    for point in points:
        assert point.get("lat") is not None
        assert point.get("lng") is not None
        assert point.get("dst") is not None
        assert point["dst"] > 0


def test_active_config_contains_at_least_five_points() -> None:
    points = _load_points(CONFIG_PATH)
    point_codes = {point["point_code"] for point in points}

    assert len(points) >= 5
    assert {"p001", "p002", "p003", "p004", "p005"}.issubset(point_codes)


def test_example_config_contains_at_least_five_target_points() -> None:
    points = _load_points(EXAMPLE_CONFIG_PATH)
    point_codes = {point["point_code"] for point in points}

    assert len(points) >= 5
    assert {"p001", "p002", "p003", "p004", "p005"}.issubset(point_codes)
