import sqlite3
from pathlib import Path

import pytest

from spendr import db
from spendr.errors import DatabaseError


def test_connect_creates_file_and_parent_folders(db_file: Path) -> None:
    assert not db_file.parent.exists()

    db.connect(db_file).close()

    assert db_file.is_file()


def test_new_database_is_at_latest_schema_version(conn: sqlite3.Connection) -> None:
    assert db.schema_version(conn) == db.SCHEMA_VERSION


def test_new_database_has_default_categories(conn: sqlite3.Connection) -> None:
    names = {row["name"] for row in conn.execute("SELECT name FROM categories")}

    assert names == set(db.DEFAULT_CATEGORIES)


def test_reconnecting_keeps_data_and_does_not_reseed(db_file: Path) -> None:
    first = db.connect(db_file)
    with first:
        first.execute("DELETE FROM categories WHERE name = 'food'")
    first.close()

    second = db.connect(db_file)
    count = second.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    second.close()

    assert count == len(db.DEFAULT_CATEGORIES) - 1


def test_foreign_keys_are_enforced(conn: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO expenses (amount, category_id, spent_on, created_at) "
            "VALUES (100, 9999, '2026-11-10', '2026-11-10T00:00:00+00:00')"
        )


@pytest.mark.parametrize("amount", [0, -5, 1.5, "abc"])
def test_schema_rejects_non_positive_or_non_integer_amounts(
    conn: sqlite3.Connection, amount: object
) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO expenses (amount, category_id, spent_on, created_at) "
            "VALUES (?, 1, '2026-11-10', '2026-11-10T00:00:00+00:00')",
            (amount,),
        )


@pytest.mark.parametrize("spent_on", ["2026-02-30", "10/11/2026", "2026-11", ""])
def test_schema_rejects_invalid_dates(conn: sqlite3.Connection, spent_on: str) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO expenses (amount, category_id, spent_on, created_at) "
            "VALUES (100, 1, ?, '2026-11-10T00:00:00+00:00')",
            (spent_on,),
        )


@pytest.mark.parametrize("month", ["2026-13", "2026-1", "2026-11-01", "nov"])
def test_schema_rejects_invalid_budget_months(conn: sqlite3.Connection, month: str) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO budgets (category_id, month, amount) VALUES (1, ?, 100)", (month,)
        )


def test_database_from_newer_version_is_refused(db_file: Path) -> None:
    connection = db.connect(db_file)
    connection.execute(f"PRAGMA user_version = {db.SCHEMA_VERSION + 1}")
    connection.close()

    with pytest.raises(DatabaseError, match="newer spendr"):
        db.connect(db_file)


def test_failed_migration_rolls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    broken = (*db.MIGRATIONS, ("CREATE TABLE extra (id INTEGER)", "THIS IS NOT SQL"))
    monkeypatch.setattr(db, "MIGRATIONS", broken)
    monkeypatch.setattr(db, "SCHEMA_VERSION", len(broken))
    connection = sqlite3.connect(":memory:")

    with pytest.raises(sqlite3.Error):
        db.migrate(connection)

    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master")}
    version = db.schema_version(connection)
    connection.close()
    assert "extra" not in tables
    assert version == len(broken) - 1


def test_file_that_is_not_a_database_gives_friendly_error(tmp_path: Path) -> None:
    path = tmp_path / "notes.db"
    path.write_text("this is definitely not sqlite " * 50)

    with pytest.raises(DatabaseError, match="not a usable spendr database"):
        db.connect(path)


@pytest.mark.parametrize(
    ("column", "value"),
    [("amount", 0), ("frequency", "hourly"), ("start_date", "2026-02-30"), ("end_date", "soon")],
)
def test_schema_rejects_invalid_recurring_expenses(
    conn: sqlite3.Connection, column: str, value: object
) -> None:
    row: dict[str, object] = {
        "amount": 100,
        "category_id": 1,
        "frequency": "monthly",
        "start_date": "2026-11-01",
        "end_date": None,
    }
    row[column] = value

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO recurring_expenses (amount, category_id, frequency, start_date, end_date) "
            "VALUES (:amount, :category_id, :frequency, :start_date, :end_date)",
            row,
        )


def test_in_memory_database_is_supported() -> None:
    connection = db.connect(":memory:")

    assert db.schema_version(connection) == db.SCHEMA_VERSION
    connection.close()


def test_existing_database_is_upgraded_without_losing_data(
    db_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    latest = db.MIGRATIONS
    monkeypatch.setattr(db, "MIGRATIONS", latest[:1])
    monkeypatch.setattr(db, "SCHEMA_VERSION", 1)
    old = db.connect(db_file)
    with old:
        old.execute(
            "INSERT INTO expenses (amount, category_id, spent_on, created_at) "
            "VALUES (100, 1, '2026-11-10', '2026-11-10T00:00:00+00:00')"
        )
    assert db.schema_version(old) == 1
    old.close()

    monkeypatch.setattr(db, "MIGRATIONS", latest)
    monkeypatch.setattr(db, "SCHEMA_VERSION", len(latest))
    upgraded = db.connect(db_file)
    version = db.schema_version(upgraded)
    amount = upgraded.execute("SELECT amount FROM expenses").fetchone()[0]
    upgraded.execute("INSERT INTO monthly_budgets (month, amount) VALUES ('2026-11', 5)")
    upgraded.close()

    assert version == len(latest)
    assert amount == 100


@pytest.mark.parametrize(("month", "amount"), [("2026-13", 100), ("2026-11", 0), ("2026-11", 1.5)])
def test_schema_rejects_invalid_overall_budgets(
    conn: sqlite3.Connection, month: str, amount: object
) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO monthly_budgets (month, amount) VALUES (?, ?)", (month, amount))
