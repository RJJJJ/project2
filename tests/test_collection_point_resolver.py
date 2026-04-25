from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.collection_point_resolver import PointResolutionError, resolve_point_code


def write_points(path: Path) -> None:
    path.write_text(
        json.dumps(
            [
                {"point_code": "p001", "name": "高士德", "district": "澳門半島"},
                {"point_code": "p002", "name": "氹仔中心", "district": "氹仔"},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_point_code_returns_directly(tmp_path: Path) -> None:
    config_path = tmp_path / "collection_points.json"
    write_points(config_path)

    point = resolve_point_code(point_code="p001", config_path=config_path)

    assert point["point_code"] == "p001"


def test_point_name_fuzzy_match(tmp_path: Path) -> None:
    config_path = tmp_path / "collection_points.json"
    write_points(config_path)

    point = resolve_point_code(point_name="士德", config_path=config_path)

    assert point["point_code"] == "p001"


def test_district_fuzzy_match(tmp_path: Path) -> None:
    config_path = tmp_path / "collection_points.json"
    write_points(config_path)

    point = resolve_point_code(district="氹", config_path=config_path)

    assert point["point_code"] == "p002"


def test_not_found_error_lists_available_points(tmp_path: Path) -> None:
    config_path = tmp_path / "collection_points.json"
    write_points(config_path)

    with pytest.raises(PointResolutionError) as exc_info:
        resolve_point_code(point_name="不存在", config_path=config_path)

    message = str(exc_info.value)
    assert "Collection point name not found" in message
    assert "Available collection points" in message
    assert "p001: 高士德" in message
