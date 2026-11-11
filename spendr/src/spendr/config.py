"""User configuration and file locations.

Both files live in the per-user application data directory. ``SPENDR_DB`` and
``SPENDR_CONFIG`` override the paths, which keeps tests away from real data.
"""

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from platformdirs import user_data_dir

from spendr.errors import ConfigError

APP_NAME = "spendr"
DB_ENV_VAR = "SPENDR_DB"
CONFIG_ENV_VAR = "SPENDR_CONFIG"
DEFAULT_CURRENCY = "UZS"
MAX_CURRENCY_LENGTH = 8


@dataclass(frozen=True, slots=True)
class Config:
    currency: str = DEFAULT_CURRENCY


def app_dir() -> Path:
    return Path(user_data_dir(APP_NAME, appauthor=False))


def db_path() -> Path:
    override = os.environ.get(DB_ENV_VAR)
    return Path(override).expanduser() if override else app_dir() / "spendr.db"


def config_path() -> Path:
    override = os.environ.get(CONFIG_ENV_VAR)
    return Path(override).expanduser() if override else app_dir() / "config.json"


def normalize_currency(value: str) -> str:
    """Return the currency code upper-cased, or raise :class:`ConfigError`."""
    code = value.strip().upper()
    if not code or len(code) > MAX_CURRENCY_LENGTH or not code.isalnum():
        raise ConfigError(
            f"Invalid currency {value!r}: use a short code of letters or digits, e.g. UZS or USD."
        )
    return code


def load_config(path: Path | None = None) -> Config:
    """Read the config file, falling back to defaults when it does not exist."""
    path = path or config_path()
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return Config()
    except OSError as exc:
        raise ConfigError(f"Cannot read config file {path}: {exc.strerror}.") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Config file {path} is not valid JSON: {exc.msg}.") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"Config file {path} must contain a JSON object.")

    currency = data.get("currency", DEFAULT_CURRENCY)
    if not isinstance(currency, str):
        raise ConfigError(f"Config file {path}: 'currency' must be a string.")
    return Config(currency=normalize_currency(currency))


def save_config(config: Config, path: Path | None = None) -> Path:
    path = path or config_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(config), indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"Cannot write config file {path}: {exc.strerror}.") from exc
    return path
