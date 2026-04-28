from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


def validate_points(points: list[dict[str, Any]], expected_count: int | None = None) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if expected_count is not None and len(points) != expected_count:
        errors.append(f"Expected {expected_count} points, found {len(points)}")
    codes = [str(point.get("point_code", "")).strip() for point in points]
    duplicate_codes = sorted(code for code, count in Counter(codes).items() if code and count > 1)
    if duplicate_codes:
        errors.append(f"duplicate point_code: {', '.join(duplicate_codes)}")
    required = ["point_code", "name", "district", "lat", "lng", "dst"]
    allowed = set(required)
    for idx, point in enumerate(points, start=1):
        label = point.get("point_code") or f"row_{idx}"
        extra = sorted(set(point) - allowed)
        if extra:
            warnings.append(f"{label}: extra fields present: {', '.join(extra)}")
        for field in required:
            if point.get(field) in (None, ""):
                errors.append(f"{label}: missing {field}")
        try:
            lat = float(point.get("lat"))
            lng = float(point.get("lng"))
            if not (-90 <= lat <= 90 and -180 <= lng <= 180):
                raise ValueError
        except (TypeError, ValueError):
            errors.append(f"{label}: invalid lat/lng")
        try:
            dst = int(float(point.get("dst")))
            if dst <= 0:
                raise ValueError
        except (TypeError, ValueError):
            errors.append(f"{label}: invalid dst")
    return {"ok": not errors, "count": len(points), "expected_count": expected_count, "errors": errors, "warnings": warnings}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate collection_points config JSON.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--expected-count", type=int, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    points = json.loads(args.config.read_text(encoding="utf-8"))
    summary = validate_points(points, args.expected_count)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
