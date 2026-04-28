from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

from scripts.discover_collection_points_from_browser import dedupe_capture_rows, make_dedupe_key

DEFAULT_CAPTURE = Path("data/discovery/collection_points_capture.jsonl")
DEFAULT_EXISTING = Path("config/collection_points.json")
DEFAULT_OUTPUT = Path("data/discovery/collection_points_45_candidate.json")
DEFAULT_REPORT = Path("COLLECTION_POINTS_DISCOVERY_REPORT.md")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def load_json_array(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def load_names_csv(path: Path | None) -> list[dict[str, Any]]:
    if not path or not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def find_existing_match(row: dict[str, Any], existing: list[dict[str, Any]], threshold_m: float = 80.0) -> dict[str, Any] | None:
    lat, lng = float(row["lat"]), float(row["lng"])
    best: tuple[float, dict[str, Any]] | None = None
    for point in existing:
        if "lat" not in point or "lng" not in point:
            continue
        d = distance_m(lat, lng, float(point["lat"]), float(point["lng"]))
        if d <= threshold_m and (best is None or d < best[0]):
            best = (d, point)
    return best[1] if best else None


def find_name_mapping(row: dict[str, Any], mappings: list[dict[str, Any]], threshold_m: float = 80.0) -> dict[str, Any] | None:
    if not mappings:
        return None
    lat, lng = float(row["lat"]), float(row["lng"])
    best: tuple[float, dict[str, Any]] | None = None
    for mapping in mappings:
        try:
            d = distance_m(lat, lng, float(mapping.get("lat", 0)), float(mapping.get("lng", 0)))
        except (TypeError, ValueError):
            continue
        dst_matches = str(mapping.get("dst", "")).strip() in ("", str(row.get("dst")))
        if d <= threshold_m and dst_matches and (best is None or d < best[0]):
            best = (d, mapping)
    return best[1] if best else None


def build_candidate_config(
    capture_rows: list[dict[str, Any]],
    existing_points: list[dict[str, Any]],
    name_mappings: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    unique_rows = dedupe_capture_rows(capture_rows)
    candidates: list[dict[str, Any]] = []
    missing_names = 0
    existing_matches = 0
    new_candidates = 0
    for idx, row in enumerate(unique_rows, start=1):
        match = find_existing_match(row, existing_points)
        mapping = find_name_mapping(row, name_mappings or [])
        if mapping:
            point_code = mapping.get("point_code") or f"candidate_{idx:03d}"
            name = mapping.get("name") or f"待命名地點 {idx:03d}"
            district = mapping.get("district") or "待確認"
            notes = mapping.get("notes", "")
        elif match:
            point_code = match.get("point_code", f"candidate_{idx:03d}")
            name = match.get("name", f"待命名地點 {idx:03d}")
            district = match.get("district", "待確認")
            notes = "matched existing config"
        else:
            point_code = f"candidate_{idx:03d}"
            name = f"待命名地點 {idx:03d}"
            district = "待確認"
            notes = "needs manual name/district review"
            missing_names += 1
        candidate = {
            "point_code": str(point_code),
            "name": str(name),
            "district": str(district),
            "lat": float(row["lat"]),
            "lng": float(row["lng"]),
            "dst": int(row["dst"]) if row.get("dst") is not None else None,
            "matched_existing": bool(match),
            "is_new_candidate": not bool(match),
            "notes": notes,
        }
        if match:
            existing_matches += 1
        else:
            new_candidates += 1
        candidates.append(candidate)
    summary = {
        "captures_total": len(capture_rows),
        "unique_points": len(unique_rows),
        "existing_matches": existing_matches,
        "new_candidates": new_candidates,
        "dst_values": sorted({row.get("dst") for row in unique_rows if row.get("dst") is not None}),
        "missing_names_count": missing_names,
    }
    return candidates, summary


def write_report(path: Path, candidates: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    lines = [
        "# Collection Points Discovery Report",
        "",
        f"- captures_total: {summary['captures_total']}",
        f"- unique_points: {summary['unique_points']}",
        f"- existing_matches: {summary['existing_matches']}",
        f"- new_candidates: {summary['new_candidates']}",
        f"- dst_values: {summary['dst_values']}",
        f"- missing_names_count: {summary['missing_names_count']}",
        "- next action: review names/districts/dst values before copying any candidate into config/collection_points.json.",
        "",
        "| index | point_code | name | district | lat | lng | dst | matched_existing | notes |",
        "|---:|---|---|---|---:|---:|---:|---|---|",
    ]
    for idx, point in enumerate(candidates, start=1):
        lines.append(
            f"| {idx} | {point['point_code']} | {point['name']} | {point['district']} | "
            f"{point['lat']} | {point['lng']} | {point.get('dst')} | {point['matched_existing']} | {point.get('notes', '')} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_builder(capture_path: Path, existing_config: Path, output_config: Path, report_path: Path, names_csv: Path | None = None) -> dict[str, Any]:
    rows = load_jsonl(capture_path)
    existing = load_json_array(existing_config)
    mappings = load_names_csv(names_csv)
    candidates, summary = build_candidate_config(rows, existing, mappings)
    output_config.parent.mkdir(parents=True, exist_ok=True)
    output_config.write_text(json.dumps(candidates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(report_path, candidates, summary)
    return {"ok": True, "output_config": str(output_config), "report_path": str(report_path), **summary}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a reviewable 45-point candidate config from browser captures.")
    parser.add_argument("--capture-path", type=Path, default=DEFAULT_CAPTURE)
    parser.add_argument("--existing-config", type=Path, default=DEFAULT_EXISTING)
    parser.add_argument("--output-config", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--names-csv", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    summary = run_builder(args.capture_path, args.existing_config, args.output_config, args.report_path, args.names_csv)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
