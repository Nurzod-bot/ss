import json
from pathlib import Path

import pytest

from spendr import config
from spendr.config import Config
from spendr.errors import ConfigError


def test_default_paths_share_the_app_folder(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(config.DB_ENV_VAR, raising=False)
    monkeypatch.delenv(config.CONFIG_ENV_VAR, raising=False)

    assert config.db_path() == config.app_dir() / "spendr.db"
    assert config.config_path() == config.app_dir() / "config.json"
    assert config.app_dir().name == "spendr"


def test_env_vars_override_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(config.DB_ENV_VAR, str(tmp_path / "test.db"))
    monkeypatch.setenv(config.CONFIG_ENV_VAR, str(tmp_path / "test.json"))

    assert config.db_path() == tmp_path / "test.db"
    assert config.config_path() == tmp_path / "test.json"


def test_empty_env_var_falls_back_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(config.DB_ENV_VAR, "")

    assert config.db_path() == config.app_dir() / "spendr.db"


def test_missing_file_gives_defaults(tmp_path: Path) -> None:
    assert config.load_config(tmp_path / "missing.json") == Config(currency="UZS")


def test_save_then_load_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "config.json"

    written = config.save_config(Config(currency="USD"), path)

    assert written == path
    assert config.load_config(path) == Config(currency="USD")


def test_load_uses_env_path_by_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(config.CONFIG_ENV_VAR, str(tmp_path / "c.json"))

    config.save_config(Config(currency="EUR"))

    assert config.load_config() == Config(currency="EUR")


def test_missing_key_uses_default_and_unknown_keys_are_ignored(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"theme": "dark"}))

    assert config.load_config(path) == Config()


def test_currency_is_normalized_on_load(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"currency": " usd "}))

    assert config.load_config(path).currency == "USD"


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("{not json", "not valid JSON"),
        ("[1, 2]", "must contain a JSON object"),
        ('{"currency": 5}', "must be a string"),
        ('{"currency": ""}', "Invalid currency"),
    ],
)
def test_invalid_file_raises_config_error(tmp_path: Path, content: str, message: str) -> None:
    path = tmp_path / "config.json"
    path.write_text(content)

    with pytest.raises(ConfigError, match=message):
        config.load_config(path)


@pytest.mark.parametrize("value", ["", "   ", "US D", "$", "TOOLONGCODE"])
def test_normalize_currency_rejects_bad_codes(value: str) -> None:
    with pytest.raises(ConfigError, match="Invalid currency"):
        config.normalize_currency(value)


def test_unreadable_and_unwritable_paths_raise_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="Cannot read"):
        config.load_config(tmp_path)  # a directory, not a file

    blocker = tmp_path / "file"
    blocker.write_text("x")
    with pytest.raises(ConfigError, match="Cannot write"):
        config.save_config(Config(), blocker / "config.json")
