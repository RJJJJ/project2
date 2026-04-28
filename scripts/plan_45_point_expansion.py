from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_CANDIDATE = Path("data/discovery/collection_points_45_candidate.json")


def parse_categories(categories: str) -> list[int]:
    values: list[int] = []
    for part in categories.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            values.extend(range(int(start), int(end) + 1))
        else:
            values.append(int(part))
    return values


def load_candidate_points(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def plan_expansion(candidate_config: Path, max_points: int = 45, categories: str = "1-19") -> dict:
    warnings: list[str] = []
    errors: list[str] = []
    points = load_candidate_points(candidate_config)
    selected = points[:max_points]
    missing_names = sum(1 for p in selected if not p.get("name") or str(p.get("name", "")).startswith("待命名"))
    dst_values = sorted({p.get("dst") for p in selected if p.get("dst") is not None})
    category_values = parse_categories(categories)
    if not candidate_config.exists():
        errors.append(f"Candidate config not found: {candidate_config}")
    if len(points) < max_points:
        errors.append(f"Need at least {max_points} candidate points, found {len(points)}")
    if missing_names:
        warnings.append(f"{missing_names} point(s) still need manual name/district review")
    if len(dst_values) > 1:
        warnings.append(f"Multiple dst values found; review before fetch: {dst_values}")
    ready = len(points) >= max_points and not any(error.startswith("Candidate config not found") for error in errors)
    return {
        "ok": not errors,
        "candidate_points": len(points),
        "ready_for_fetch": ready,
        "missing_names": missing_names,
        "dst_values": dst_values,
        "estimated_api_requests": max_points * len(category_values),
        "warnings": warnings,
        "errors": errors,
        "recommended_commands": [
            f"python scripts\\fetch_full_category_points.py --max-points {max_points} --categories {categories} --config {candidate_config} --dry-run",
            f"python scripts\\fetch_full_category_points.py --max-points {max_points} --categories {categories} --config {candidate_config}",
            f"python scripts\\generate_full_category_coverage_report.py --max-points {max_points} --config {candidate_config}",
            f"python scripts\\import_processed_to_sqlite.py --date latest --max-points {max_points} --config {candidate_config}",
        ],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan Project2 45 collection point expansion.")
    parser.add_argument("--candidate-config", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--max-points", type=int, default=45)
    parser.add_argument("--categories", default="1-19")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    summary = plan_expansion(args.candidate_config, args.max_points, args.categories)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
