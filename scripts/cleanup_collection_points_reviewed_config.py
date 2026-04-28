from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

DEFAULT_INPUT = Path("data/discovery/collection_points_46_reviewed_manual.json")
DEFAULT_OUTPUT = Path("data/discovery/collection_points_46_cleaned.json")
DEFAULT_REPORT = Path("COLLECTION_POINTS_CLEANUP_REPORT.md")

TAIPA_HINTS = ("氹仔", "花城", "馬會", "金利達", "湖畔", "海洋", "中央公園")
COLOANE_HINTS = ("路環", "金峰南岸")


def normalize_string(value: Any) -> str:
    return str(value or "").strip()


def normalize_district_broad(name: str, district: str, warnings: list[str], point_code: str) -> str:
    text = f"{name} {district}".strip()
    if any(hint in text for hint in TAIPA_HINTS):
        return "氹仔"
    if any(hint in text for hint in COLOANE_HINTS):
        return "路環"
    if district in ("澳門半島", "北區", "中區", "下環", "三盞燈", "筷子基", "關閘", "高士德", "台山", "黑沙環"):
        return "澳門半島"
    if district:
        warnings.append(f"{point_code}: district '{district}' treated as 澳門半島; review if needed")
        return "澳門半島"
    warnings.append(f"{point_code}: missing district treated as 澳門半島; review if needed")
    return "澳門半島"


def resolve_dst(row: dict[str, Any], policy: str) -> int | None:
    if policy == "force-400":
        return 400
    if policy == "force-500":
        return 500
    if policy == "use-captured":
        for key in ("captured_dst", "capture_dst", "original_dst", "dst_captured"):
            if row.get(key) not in (None, ""):
                return int(float(row[key]))
    if row.get("dst") in (None, ""):
        return None
    return int(float(row["dst"]))


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def clean_points(
    rows: list[dict[str, Any]],
    *,
    target_count: int = 45,
    normalize_district: bool = True,
    district_mode: str = "broad",
    dst_policy: str = "force-400",
    duplicate_threshold_meters: float = 150.0,
    drop_point_codes: list[str] | None = None,
) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []
    drop_set = set(drop_point_codes or [])
    cleaned: list[dict[str, Any]] = []

    for row in rows:
        point_code = normalize_string(row.get("point_code"))
        if not point_code:
            errors.append("Missing point_code")
            continue
        if point_code in drop_set:
            continue
        name = normalize_string(row.get("name"))
        district = normalize_string(row.get("district"))
        if not name:
            errors.append(f"{point_code}: missing name")
        try:
            lat = float(row.get("lat"))
            lng = float(row.get("lng"))
            if not (-90 <= lat <= 90 and -180 <= lng <= 180):
                raise ValueError("coordinate out of range")
        except (TypeError, ValueError):
            errors.append(f"{point_code}: invalid lat/lng")
            lat = 0.0
            lng = 0.0
        try:
            dst = resolve_dst(row, dst_policy)
        except (TypeError, ValueError):
            errors.append(f"{point_code}: invalid dst")
            dst = None
        if normalize_district and district_mode == "broad":
            district = normalize_district_broad(name, district, warnings, point_code)
        # keep mode only trims.
        cleaned.append({"point_code": point_code, "name": name, "district": district, "lat": lat, "lng": lng, "dst": dst})

    counts = Counter(point["point_code"] for point in cleaned)
    duplicates_codes = sorted(code for code, count in counts.items() if count > 1)
    if duplicates_codes:
        errors.append(f"duplicate point_code: {', '.join(duplicates_codes)}")

    possible_duplicates: list[dict[str, Any]] = []
    for i, point_a in enumerate(cleaned):
        for point_b in cleaned[i + 1 :]:
            distance = haversine_m(point_a["lat"], point_a["lng"], point_b["lat"], point_b["lng"])
            if distance < duplicate_threshold_meters:
                possible_duplicates.append(
                    {
                        "point_a": f"{point_a['point_code']} {point_a['name']}",
                        "point_b": f"{point_b['point_code']} {point_b['name']}",
                        "distance_m": round(distance, 1),
                    }
                )

    output_count = len(cleaned)
    if output_count > target_count:
        warnings.append(
            f"Point count {output_count} exceeds target count {target_count}. Review possible duplicates and decide one point to drop."
        )
    elif output_count < target_count:
        warnings.append(f"Point count {output_count} is below target count {target_count}.")
    if dst_policy == "force-400":
        warnings.append("dst normalized to 400 for all points.")
    elif dst_policy == "force-500":
        warnings.append("dst normalized to 500 for all points.")

    if errors:
        status = "failed"
    elif output_count == target_count:
        status = "ready"
    else:
        status = "needs_review"

    return {
        "ok": not errors,
        "status": status,
        "input_count": len(rows),
        "output_count": output_count,
        "target_count": target_count,
        "dst_values": sorted({point["dst"] for point in cleaned if point.get("dst") is not None}),
        "districts": dict(Counter(point["district"] for point in cleaned)),
        "possible_duplicates_count": len(possible_duplicates),
        "possible_duplicates": possible_duplicates,
        "warnings": warnings,
        "errors": errors,
        "points": cleaned,
    }


def write_report(path: Path, *, input_path: Path, output_path: Path, summary: dict[str, Any], dst_policy: str, district_mode: str) -> None:
    lines = [
        "# Collection Points Cleanup Report",
        "",
        f"- input file: `{input_path}`",
        f"- output file: `{output_path}`",
        f"- target count: {summary['target_count']}",
        f"- status: {summary['status']}",
        f"- dst policy: {dst_policy}",
        f"- district mode: {district_mode}",
        f"- dst values: {summary['dst_values']}",
        "",
        "## District summary",
        "",
    ]
    for district, count in summary["districts"].items():
        lines.append(f"- {district}: {count}")
    lines.extend(["", "## Possible duplicates", "", "| point_a | point_b | distance_m |", "|---|---|---:|"])
    if summary["possible_duplicates"]:
        for dup in summary["possible_duplicates"]:
            lines.append(f"| {dup['point_a']} | {dup['point_b']} | {dup['distance_m']} |")
    else:
        lines.append("| none | none | 0 |")
    lines.extend(["", "## Final points", "", "| point_code | name | district | lat | lng | dst |", "|---|---|---|---:|---:|---:|"])
    for point in summary["points"]:
        lines.append(f"| {point['point_code']} | {point['name']} | {point['district']} | {point['lat']} | {point['lng']} | {point['dst']} |")
    if summary["warnings"]:
        lines.extend(["", "## Warnings", ""] + [f"- {warning}" for warning in summary["warnings"]])
    if summary["errors"]:
        lines.extend(["", "## Errors", ""] + [f"- {error}" for error in summary["errors"]])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_cleanup(args: argparse.Namespace) -> dict[str, Any]:
    input_path = Path(args.input)
    output_path = Path(args.output)
    report_path = Path(args.report_path)
    if not input_path.exists():
        summary = {
            "ok": False,
            "status": "failed",
            "input_count": 0,
            "output_count": 0,
            "target_count": args.target_count,
            "dst_values": [],
            "districts": {},
            "possible_duplicates_count": 0,
            "possible_duplicates": [],
            "warnings": [],
            "errors": [f"Input file not found: {input_path}. Provide --input."],
            "output": str(output_path),
            "report_path": str(report_path),
        }
        return summary
    rows = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("Input JSON must be an array")
    summary = clean_points(
        rows,
        target_count=args.target_count,
        normalize_district=args.normalize_district,
        district_mode=args.district_mode,
        dst_policy=args.dst_policy,
        duplicate_threshold_meters=args.duplicate_threshold_meters,
        drop_point_codes=args.drop_point_code,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary["points"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(report_path, input_path=input_path, output_path=output_path, summary=summary, dst_policy=args.dst_policy, district_mode=args.district_mode)
    public_summary = {k: v for k, v in summary.items() if k != "points"}
    public_summary["output"] = str(output_path)
    public_summary["report_path"] = str(report_path)
    return public_summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean and validate reviewed 46-point collection config without overwriting production config.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT))
    parser.add_argument("--target-count", type=int, default=45)
    parser.add_argument("--normalize-district", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--district-mode", choices=["broad", "keep"], default="broad")
    parser.add_argument("--dst-policy", choices=["keep", "use-captured", "force-400", "force-500"], default="force-400")
    parser.add_argument("--duplicate-threshold-meters", type=float, default=150.0)
    parser.add_argument("--drop-point-code", action="append", default=[])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    summary = run_cleanup(args)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
