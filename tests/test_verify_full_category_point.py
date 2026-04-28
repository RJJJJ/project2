from __future__ import annotations

from pathlib import Path

from scripts.verify_full_category_point import EXPECTED_FILES, resolve_latest_date, verify_full_category_point


def _write(path: Path, lines: int = 1) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join('{"ok": true}' for _ in range(lines)) + ("\n" if lines else ""), encoding="utf-8")


def test_all_files_exist_ok_true(tmp_path: Path) -> None:
    point_dir = tmp_path / "2026-04-28" / "p001"
    for name in EXPECTED_FILES:
        _write(point_dir / name)

    report = verify_full_category_point(date="2026-04-28", point_code="p001", processed_root=tmp_path)

    assert report["ok"] is True
    assert report["missing_files"] == []
    assert len(report["files"]) == 19


def test_missing_files_ok_false(tmp_path: Path) -> None:
    point_dir = tmp_path / "2026-04-28" / "p001"
    _write(point_dir / "category_1_prices.jsonl")

    report = verify_full_category_point(date="2026-04-28", point_code="p001", processed_root=tmp_path)

    assert report["ok"] is False
    assert "category_2_prices.jsonl" in report["missing_files"]
    assert "supermarkets.jsonl" in report["missing_files"]


def test_zero_row_file_warns_but_ok(tmp_path: Path) -> None:
    point_dir = tmp_path / "2026-04-28" / "p001"
    for name in EXPECTED_FILES:
        _write(point_dir / name, lines=0 if name == "category_2_prices.jsonl" else 1)

    report = verify_full_category_point(date="2026-04-28", point_code="p001", processed_root=tmp_path)

    assert report["ok"] is True
    assert "zero rows: category_2_prices.jsonl" in report["warnings"]


def test_latest_date_resolve(tmp_path: Path) -> None:
    (tmp_path / "2026-04-27").mkdir()
    (tmp_path / "2026-04-28").mkdir()

    assert resolve_latest_date(tmp_path) == "2026-04-28"
