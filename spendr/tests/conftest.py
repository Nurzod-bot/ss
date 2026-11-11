import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from spendr import db
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
