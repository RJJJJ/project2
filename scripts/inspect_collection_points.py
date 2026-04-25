from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from services.collection_point_resolver import DEFAULT_COLLECTION_POINTS_PATH, load_collection_points


def inspect_collection_points(config_path: Path = DEFAULT_COLLECTION_POINTS_PATH) -> dict[str, Any]:
    points = load_collection_points(config_path)
    return {
        "total_points": len(points),
        "points": [
            {
                "point_code": point.get("point_code"),
                "name": point.get("name"),
                "district": point.get("district"),
                "lat": point.get("lat"),
                "lng": point.get("lng"),
                "dst": point.get("dst"),
            }
            for point in points
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect configured collection points.")
    parser.add_argument("--config", default=str(DEFAULT_COLLECTION_POINTS_PATH))
    args = parser.parse_args()

    print(json.dumps(inspect_collection_points(Path(args.config)), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
