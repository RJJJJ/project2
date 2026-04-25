from __future__ import annotations

from pathlib import Path

from app import utils


def _write_demo_file(root: Path) -> None:
    point_dir = root / "2026-04-25" / "p001"
    point_dir.mkdir(parents=True)
    (point_dir / "category_1_prices.jsonl").write_text('{"product_oid": 1}\n', encoding="utf-8")


def test_processed_root_env_takes_priority(monkeypatch, tmp_path) -> None:
    env_root = tmp_path / "env_processed"
    monkeypatch.setenv("PROCESSED_ROOT", str(env_root))

    assert utils.get_processed_root() == env_root


def test_processed_root_uses_data_processed_when_available(monkeypatch, tmp_path) -> None:
    data_root = tmp_path / "data" / "processed"
    demo_root = tmp_path / "demo_data" / "processed"
    _write_demo_file(data_root)
    _write_demo_file(demo_root)
    monkeypatch.delenv("PROCESSED_ROOT", raising=False)
    monkeypatch.setattr(utils, "DEFAULT_PROCESSED_ROOT", data_root)
    monkeypatch.setattr(utils, "DEMO_PROCESSED_ROOT", demo_root)

    assert utils.get_processed_root() == data_root


def test_processed_root_falls_back_to_demo_data(monkeypatch, tmp_path) -> None:
    data_root = tmp_path / "data" / "processed"
    demo_root = tmp_path / "demo_data" / "processed"
    _write_demo_file(demo_root)
    monkeypatch.delenv("PROCESSED_ROOT", raising=False)
    monkeypatch.setattr(utils, "DEFAULT_PROCESSED_ROOT", data_root)
    monkeypatch.setattr(utils, "DEMO_PROCESSED_ROOT", demo_root)

    assert utils.get_processed_root() == demo_root
