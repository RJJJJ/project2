from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COLLECTION_POINTS_PATH = PROJECT_ROOT / "config" / "collection_points.json"


class PointResolutionError(ValueError):
    pass


def load_collection_points(config_path: str | Path | None = None) -> list[dict[str, Any]]:
    path = Path(config_path) if config_path else DEFAULT_COLLECTION_POINTS_PATH
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def _matches(value: Any, query: str) -> bool:
    normalized_value = str(value or "").casefold()
    normalized_query = query.strip().casefold()
    return bool(normalized_query) and normalized_query in normalized_value


def _available_points_message(points: list[dict[str, Any]]) -> str:
    if not points:
        return "No collection points are configured."
    lines = ["Available collection points:"]
    for point in points:
        lines.append(
            f"- {point.get('point_code')}: {point.get('name')} ({point.get('district')})"
        )
    return "\n".join(lines)


def resolve_point_code(
    point_code: str | None = None,
    point_name: str | None = None,
    district: str | None = None,
    config_path: str | Path | None = None,
) -> dict[str, Any]:
    points = load_collection_points(config_path)

    if point_code:
        for point in points:
            if str(point.get("point_code")) == point_code:
                return point
        return {"point_code": point_code, "name": point_code, "district": None}

    if point_name:
        for point in points:
            if _matches(point.get("name"), point_name):
                return point
        raise PointResolutionError(
            f"Collection point name not found: {point_name}\n{_available_points_message(points)}"
        )

    if district:
        for point in points:
            if _matches(point.get("district"), district):
                return point
        raise PointResolutionError(
            f"Collection point district not found: {district}\n{_available_points_message(points)}"
        )

    raise PointResolutionError(
        "Please provide --point-code, --point-name, or --district.\n"
        f"{_available_points_message(points)}"
    )
