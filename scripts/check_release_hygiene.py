from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Callable, Iterable, Any

REPO_ROOT = Path(__file__).resolve().parents[1]
OPTIONAL_REPORTS_MD = [
    "UPDATE_REPORT.md",
    "COVERAGE_REPORT.md",
    "FULL_CATEGORY_COVERAGE_REPORT.md",
    "WEEKLY_REFRESH_REPORT.md",
]
OPTIONAL_REPORTS_JSON = [
    "data/reports/update_report.json",
    "data/reports/coverage_report.json",
    "data/reports/full_category_coverage_report.json",
    "data/reports/weekly_refresh_report.json",
]
FORBIDDEN_TRACKED_PREFIXES = [
    "data/raw/",
    "data/processed/",
    "node_modules/",
    ".venv/",
    "venv/",
    "test_tmp/",
]
FORBIDDEN_TRACKED_SQLITE = ["data/app_state/"]

Check = dict[str, Any]
GitLsFiles = Callable[[Path], list[str]]


def default_git_ls_files(repo_root: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "git ls-files failed")
    return [line.strip().replace("\\", "/") for line in proc.stdout.splitlines() if line.strip()]


def add_check(checks: list[Check], name: str, ok: bool, detail: str, *, blocking: bool = True) -> None:
    checks.append({"name": name, "ok": bool(ok), "detail": detail, "blocking": blocking})


def load_expected_points(repo_root: Path, limit: int = 15) -> list[str]:
    config_path = repo_root / "config" / "collection_points.json"
    if not config_path.exists():
        return [f"p{i:03d}" for i in range(1, limit + 1)]
    data = json.loads(config_path.read_text(encoding="utf-8"))
    points = [str(item.get("point_code")) for item in data if item.get("point_code")]
    return points[:limit] or [f"p{i:03d}" for i in range(1, limit + 1)]


def latest_date_dir(processed_root: Path) -> Path | None:
    if not processed_root.exists():
        return None
    dirs = sorted([p for p in processed_root.iterdir() if p.is_dir()], key=lambda p: p.name)
    return dirs[-1] if dirs else None


def tracked_forbidden_files(tracked_files: Iterable[str]) -> list[str]:
    bad: list[str] = []
    for path in tracked_files:
        normalized = path.replace("\\", "/")
        if any(normalized.startswith(prefix) for prefix in FORBIDDEN_TRACKED_PREFIXES):
            bad.append(normalized)
            continue
        if any(normalized.startswith(prefix) and normalized.endswith(".sqlite3") for prefix in FORBIDDEN_TRACKED_SQLITE):
            bad.append(normalized)
    return sorted(bad)


def run_release_hygiene(repo_root: Path = REPO_ROOT, git_ls_files: GitLsFiles = default_git_ls_files) -> dict[str, Any]:
    checks: list[Check] = []
    warnings: list[str] = []
    errors: list[str] = []

    processed_root = repo_root / "demo_data" / "processed"
    add_check(checks, "demo_data_exists", processed_root.exists(), str(processed_root))

    latest_dir = latest_date_dir(processed_root)
    add_check(
        checks,
        "demo_data_latest_date",
        latest_dir is not None,
        latest_dir.name if latest_dir else "No dated directory under demo_data/processed",
    )

    expected_points = load_expected_points(repo_root, 15)
    if latest_dir:
        missing_points = [point for point in expected_points if not (latest_dir / point).is_dir()]
        add_check(
            checks,
            "demo_points_15",
            not missing_points,
            f"expected={expected_points}; missing={missing_points}",
        )
        for point in expected_points:
            point_dir = latest_dir / point
            if not point_dir.is_dir():
                continue
            supermarkets = point_dir / "supermarkets.jsonl"
            add_check(
                checks,
                f"{point}_supermarkets",
                supermarkets.exists() and supermarkets.stat().st_size > 0,
                str(supermarkets.relative_to(repo_root)),
            )
            category_files = sorted(point_dir.glob("category_*_prices.jsonl"))
            add_check(
                checks,
                f"{point}_category_files",
                bool(category_files),
                f"{len(category_files)} category price file(s)",
            )
            category_nums = {int(p.name.split("_")[1]) for p in category_files if p.name.split("_")[1].isdigit()}
            if len(category_nums) >= 18 or 18 in category_nums:
                missing_categories = [i for i in range(1, 19) if i not in category_nums]
                add_check(
                    checks,
                    f"{point}_full_categories_1_18",
                    not missing_categories,
                    f"missing={missing_categories}",
                )
    else:
        add_check(checks, "demo_points_15", False, "No latest demo data directory")

    for rel in OPTIONAL_REPORTS_MD + OPTIONAL_REPORTS_JSON:
        exists = (repo_root / rel).exists()
        add_check(checks, f"report_{rel.replace('/', '_')}", exists, rel, blocking=False)
        if not exists:
            warnings.append(f"Optional report missing: {rel}")

    try:
        tracked = git_ls_files(repo_root)
        bad = tracked_forbidden_files(tracked)
        add_check(
            checks,
            "forbidden_tracked_files",
            not bad,
            "No forbidden generated/runtime files are tracked" if not bad else "; ".join(bad[:20]),
        )
    except Exception as exc:  # pragma: no cover - defensive CLI behavior
        add_check(checks, "git_ls_files", False, str(exc))

    for check in checks:
        if check.get("blocking", True) and not check["ok"]:
            errors.append(f"{check['name']}: {check['detail']}")

    return {"ok": not errors, "checks": checks, "warnings": warnings, "errors": errors}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Project2 v1.0-prep release hygiene.")
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="Repository root; defaults to this script's parent.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = run_release_hygiene(Path(args.repo_root).resolve())
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
