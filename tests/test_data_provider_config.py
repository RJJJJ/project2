from pathlib import Path


def test_default_provider_is_jsonl(monkeypatch) -> None:
    monkeypatch.delenv("PROJECT2_DATA_PROVIDER", raising=False)
    from services.data_provider_config import get_data_provider, is_sqlite_provider_enabled

    assert get_data_provider() == "jsonl"
    assert is_sqlite_provider_enabled() is False


def test_sqlite_provider_enabled(monkeypatch) -> None:
    monkeypatch.setenv("PROJECT2_DATA_PROVIDER", "sqlite")
    from services.data_provider_config import get_data_provider, is_sqlite_provider_enabled

    assert get_data_provider() == "sqlite"
    assert is_sqlite_provider_enabled() is True


def test_invalid_provider_falls_back_to_jsonl(monkeypatch) -> None:
    monkeypatch.setenv("PROJECT2_DATA_PROVIDER", "bad")
    from services.data_provider_config import get_data_provider

    assert get_data_provider() == "jsonl"


def test_sqlite_db_path_env(monkeypatch, tmp_path: Path) -> None:
    path = tmp_path / "x.sqlite3"
    monkeypatch.setenv("PROJECT2_SQLITE_DB_PATH", str(path))
    from services.data_provider_config import get_sqlite_db_path

    assert get_sqlite_db_path() == path
