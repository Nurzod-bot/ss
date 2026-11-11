"""SQLite connection handling and schema migrations.

The schema version is tracked with ``PRAGMA user_version``. Each entry in
:data:`MIGRATIONS` moves the database forward by exactly one version and is
applied inside a transaction, so a failed upgrade leaves the file untouched.
"""

import sqlite3
from pathlib import Path

from spendr.errors import DatabaseError

DEFAULT_CATEGORIES: tuple[str, ...] = (
    "food",
    "transport",
    "housing",
    "utilities",
    "health",
    "entertainment",
    "shopping",
    "other",
)

MIGRATIONS: tuple[tuple[str, ...], ...] = (
    # 1: initial schema
    (
        """
        CREATE TABLE categories (
            id   INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE CHECK (length(trim(name)) > 0)
        )
        """,
        """
        CREATE TABLE expenses (
            id          INTEGER PRIMARY KEY,
            amount      INTEGER NOT NULL CHECK (typeof(amount) = 'integer' AND amount > 0),
            category_id INTEGER NOT NULL REFERENCES categories (id) ON DELETE RESTRICT,
            note        TEXT    NOT NULL DEFAULT '',
            spent_on    TEXT    NOT NULL CHECK (spent_on IS date(spent_on)),
            created_at  TEXT    NOT NULL
        )
        """,
        "CREATE INDEX idx_expenses_spent_on ON expenses (spent_on)",
        "CREATE INDEX idx_expenses_category ON expenses (category_id)",
        """
        CREATE TABLE budgets (
            id          INTEGER PRIMARY KEY,
            category_id INTEGER NOT NULL REFERENCES categories (id) ON DELETE CASCADE,
            month       TEXT    NOT NULL CHECK (month || '-01' IS date(month || '-01')),
            amount      INTEGER NOT NULL CHECK (typeof(amount) = 'integer' AND amount > 0),
            UNIQUE (category_id, month)
        )
        """,
        "INSERT INTO categories (name) VALUES "
        + ", ".join(f"('{name}')" for name in DEFAULT_CATEGORIES),
    ),
    # 2: one overall spending limit per month, independent of the category budgets
    (
        """
        CREATE TABLE monthly_budgets (
            month  TEXT    PRIMARY KEY CHECK (month || '-01' IS date(month || '-01')),
            amount INTEGER NOT NULL CHECK (typeof(amount) = 'integer' AND amount > 0)
        ) WITHOUT ROWID
        """,
    ),
    # 3: templates that turn into real expenses each time they fall due
    (
        """
        CREATE TABLE recurring_expenses (
            id          INTEGER PRIMARY KEY,
            amount      INTEGER NOT NULL CHECK (typeof(amount) = 'integer' AND amount > 0),
            category_id INTEGER NOT NULL REFERENCES categories (id) ON DELETE RESTRICT,
            note        TEXT    NOT NULL DEFAULT '',
            frequency   TEXT    NOT NULL
                        CHECK (frequency IN ('daily', 'weekly', 'monthly', 'yearly')),
            start_date  TEXT    NOT NULL CHECK (start_date IS date(start_date)),
            end_date    TEXT    CHECK (end_date IS NULL OR end_date IS date(end_date)),
            last_posted TEXT    CHECK (last_posted IS NULL OR last_posted IS date(last_posted))
        )
        """,
    ),
)

SCHEMA_VERSION = len(MIGRATIONS)


def connect(path: Path | str) -> sqlite3.Connection:
    """Open the database at ``path``, creating and migrating it as needed.

    Pass ``":memory:"`` for a throwaway in-memory database.
    """
    if str(path) != ":memory:":
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise DatabaseError(f"Cannot create database folder for {path}: {exc}.") from exc
    try:
        conn = sqlite3.connect(path)
    except sqlite3.Error as exc:
        raise DatabaseError(f"Cannot open database {path}: {exc}.") from exc

    conn.row_factory = sqlite3.Row
    try:
        # Off by default in SQLite, and it is a per-connection setting.
        conn.execute("PRAGMA foreign_keys = ON")
        migrate(conn)
    except sqlite3.Error as exc:
        conn.close()
        raise DatabaseError(f"{path} is not a usable spendr database: {exc}.") from exc
    except DatabaseError:
        conn.close()
        raise
    return conn


def schema_version(conn: sqlite3.Connection) -> int:
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


def migrate(conn: sqlite3.Connection) -> None:
    """Apply every migration newer than the database's current version."""
    current = schema_version(conn)
    if current > SCHEMA_VERSION:
        raise DatabaseError(
            f"This database was created by a newer spendr (schema v{current}, "
            f"this version supports up to v{SCHEMA_VERSION}). Please upgrade spendr."
        )
    for version in range(current + 1, SCHEMA_VERSION + 1):
        with conn:
            # The sqlite3 module only opens a transaction implicitly before DML,
            # so start one by hand to make the DDL statements atomic as well.
            conn.execute("BEGIN")
            for statement in MIGRATIONS[version - 1]:
                conn.execute(statement)
            conn.execute(f"PRAGMA user_version = {version}")
