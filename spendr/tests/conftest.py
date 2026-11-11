import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from spendr import config, db
from spendr.repository import BudgetRepository, CategoryRepository, ExpenseRepository


@pytest.fixture
def db_file(tmp_path: Path) -> Path:
    return tmp_path / "data" / "spendr.db"


@pytest.fixture
def conn(db_file: Path) -> Iterator[sqlite3.Connection]:
    connection = db.connect(db_file)
    yield connection
    connection.close()


@pytest.fixture
def categories(conn: sqlite3.Connection) -> CategoryRepository:
    return CategoryRepository(conn)


@pytest.fixture
def expenses(conn: sqlite3.Connection) -> ExpenseRepository:
    return ExpenseRepository(conn)


@pytest.fixture
def budgets(conn: sqlite3.Connection) -> BudgetRepository:
    return BudgetRepository(conn)


@pytest.fixture(autouse=True)
def cli_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Point the app at a throwaway database and config file.

    Applied to every test so that nothing can ever touch the real user data.
    """
    monkeypatch.setenv(config.DB_ENV_VAR, str(tmp_path / "cli.db"))
    monkeypatch.setenv(config.CONFIG_ENV_VAR, str(tmp_path / "config.json"))
    monkeypatch.setenv("COLUMNS", "120")
    return tmp_path
