from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "collection_points.json"
EXPECTED_POINT_COUNT = 46
EXPECTED_DST_VALUES = {400}
MACAU_LAT_RANGE = (22.05, 22.25)
MACAU_LNG_RANGE = (113.45, 113.65)
VALID_DISTRICTS = {
    "\u6fb3\u9580\u534a\u5cf6",
    "\u5317\u5340",
    "\u4e2d\u5340",
    "\u5357\u5340",
    "\u4e0b\u74b0",
    "\u4e09\u76de\u71c8",
    "\u96c5\u5ec9\u8a2a",
    "\u9ad8\u58eb\u5fb7",
    "\u5357\u7063",
    "\u6c39\u4ed4",
    "\u8def\u74b0",
    "\u6fb3\u5927",
}


def _load_points(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_active_config_contains_official_46_points() -> None:
    points = _load_points(CONFIG_PATH)

    assert len(points) == EXPECTED_POINT_COUNT


def test_active_point_codes_are_unique_and_sequential() -> None:
    points = _load_points(CONFIG_PATH)
    point_codes = [point["point_code"] for point in points]
    expected_point_codes = [f"p{index:03d}" for index in range(1, EXPECTED_POINT_COUNT + 1)]

    assert len(point_codes) == len(set(point_codes))
    assert point_codes == expected_point_codes


def test_active_points_have_non_empty_names() -> None:
    points = _load_points(CONFIG_PATH)

    for point in points:
        name = point.get("name")
        assert isinstance(name, str)
        assert name
        assert name == name.strip()


def test_active_points_have_valid_districts() -> None:
    points = _load_points(CONFIG_PATH)

    for point in points:
        district = point.get("district")
        assert isinstance(district, str)
        assert district
        assert district == district.strip()
        assert district != "\u5f85\u78ba\u8a8d"
        assert district in VALID_DISTRICTS


def test_active_points_have_required_coordinates_and_supported_radius() -> None:
    points = _load_points(CONFIG_PATH)
    dst_values = set()

    for point in points:
        lat = point.get("lat")
        lng = point.get("lng")
        dst = point.get("dst")

        assert isinstance(lat, (int, float))
        assert isinstance(lng, (int, float))
        assert MACAU_LAT_RANGE[0] <= lat <= MACAU_LAT_RANGE[1]
        assert MACAU_LNG_RANGE[0] <= lng <= MACAU_LNG_RANGE[1]
        assert isinstance(dst, int)
        assert 100 <= dst <= 1000
        dst_values.add(dst)

    assert dst_values == EXPECTED_DST_VALUES
