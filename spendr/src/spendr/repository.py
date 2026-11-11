"""All SQL lives here. Repositories take and return models, never raw rows.

Inputs are assumed to be already validated by the service layer; the database
constraints are a safety net, not the place where user errors are reported.
"""

import sqlite3
from datetime import UTC, date, datetime

from spendr.errors import CategoryInUseError, DuplicateError, NotFoundError
from spendr.models import Budget, Category, CategoryTotal, Expense, ExpenseFilter

_EXPENSE_SELECT = """
    SELECT e.id, e.amount, e.category_id, c.name AS category, e.note, e.spent_on, e.created_at
    FROM expenses AS e
    JOIN categories AS c ON c.id = e.category_id
"""

_BUDGET_SELECT = """
    SELECT b.id, b.category_id, c.name AS category, b.month, b.amount
    FROM budgets AS b
    JOIN categories AS c ON c.id = b.category_id
"""


def _category(row: sqlite3.Row) -> Category:
    return Category(id=int(row["id"]), name=str(row["name"]))


def _expense(row: sqlite3.Row) -> Expense:
    return Expense(
        id=int(row["id"]),
        amount=int(row["amount"]),
        category_id=int(row["category_id"]),
        category=str(row["category"]),
        note=str(row["note"]),
        spent_on=date.fromisoformat(row["spent_on"]),
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _budget(row: sqlite3.Row) -> Budget:
    return Budget(
        id=int(row["id"]),
        category_id=int(row["category_id"]),
        category=str(row["category"]),
        month=str(row["month"]),
        amount=int(row["amount"]),
    )


class CategoryRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(self, name: str) -> Category:
        try:
            with self._conn:
                cursor = self._conn.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        except sqlite3.IntegrityError as exc:
            raise DuplicateError(f"Category '{name}' already exists.") from exc
        assert cursor.lastrowid is not None
        return Category(id=cursor.lastrowid, name=name)

    def get(self, category_id: int) -> Category | None:
        row = self._conn.execute(
            "SELECT id, name FROM categories WHERE id = ?", (category_id,)
        ).fetchone()
        return _category(row) if row else None

    def get_by_name(self, name: str) -> Category | None:
        """Look a category up by name, ignoring case."""
        row = self._conn.execute(
            "SELECT id, name FROM categories WHERE name = ?", (name,)
        ).fetchone()
        return _category(row) if row else None

    def list_all(self) -> list[Category]:
        rows = self._conn.execute("SELECT id, name FROM categories ORDER BY name").fetchall()
        return [_category(row) for row in rows]

    def rename(self, category_id: int, new_name: str) -> Category:
        try:
            with self._conn:
                cursor = self._conn.execute(
                    "UPDATE categories SET name = ? WHERE id = ?", (new_name, category_id)
                )
        except sqlite3.IntegrityError as exc:
            raise DuplicateError(f"Category '{new_name}' already exists.") from exc
        if cursor.rowcount == 0:
            raise NotFoundError(f"No category with id {category_id}.")
        return Category(id=category_id, name=new_name)

    def expense_count(self, category_id: int) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) FROM expenses WHERE category_id = ?", (category_id,)
        ).fetchone()
        return int(row[0])

    def remove(self, category_id: int) -> None:
        """Delete a category and its budgets. Refuses while expenses reference it."""
        try:
            with self._conn:
                cursor = self._conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        except sqlite3.IntegrityError as exc:
            count = self.expense_count(category_id)
            raise CategoryInUseError(
                f"Category is still used by {count} expense(s); move or delete them first."
            ) from exc
        if cursor.rowcount == 0:
            raise NotFoundError(f"No category with id {category_id}.")


class ExpenseRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(self, amount: int, category_id: int, note: str, spent_on: date) -> Expense:
        created_at = datetime.now(UTC).isoformat(timespec="seconds")
        with self._conn:
            cursor = self._conn.execute(
                "INSERT INTO expenses (amount, category_id, note, spent_on, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (amount, category_id, note, spent_on.isoformat(), created_at),
            )
        assert cursor.lastrowid is not None
        return self._require(cursor.lastrowid)

    def get(self, expense_id: int) -> Expense | None:
        row = self._conn.execute(f"{_EXPENSE_SELECT} WHERE e.id = ?", (expense_id,)).fetchone()
        return _expense(row) if row else None

    def find(self, filters: ExpenseFilter | None = None) -> list[Expense]:
        """Return matching expenses, newest first."""
        filters = filters or ExpenseFilter()
        clauses: list[str] = []
        params: list[int | str] = []
        if filters.category_id is not None:
            clauses.append("e.category_id = ?")
            params.append(filters.category_id)
        if filters.date_from is not None:
            clauses.append("e.spent_on >= ?")
            params.append(filters.date_from.isoformat())
        if filters.date_to is not None:
            clauses.append("e.spent_on <= ?")
            params.append(filters.date_to.isoformat())

        sql = _EXPENSE_SELECT
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY e.spent_on DESC, e.id DESC"
        if filters.limit is not None:
            sql += " LIMIT ?"
            params.append(filters.limit)
        return [_expense(row) for row in self._conn.execute(sql, params).fetchall()]

    def update(
        self,
        expense_id: int,
        *,
        amount: int | None = None,
        category_id: int | None = None,
        note: str | None = None,
        spent_on: date | None = None,
    ) -> Expense:
        """Change only the fields that are given; ``None`` means "leave as is"."""
        changes: dict[str, int | str] = {}
        if amount is not None:
            changes["amount"] = amount
        if category_id is not None:
            changes["category_id"] = category_id
        if note is not None:
            changes["note"] = note
        if spent_on is not None:
            changes["spent_on"] = spent_on.isoformat()

        if changes:
            # Column names come from the fixed set above, never from user input.
            assignments = ", ".join(f"{column} = ?" for column in changes)
            with self._conn:
                self._conn.execute(
                    f"UPDATE expenses SET {assignments} WHERE id = ?",
                    (*changes.values(), expense_id),
                )
        return self._require(expense_id)

    def delete(self, expense_id: int) -> None:
        with self._conn:
            cursor = self._conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        if cursor.rowcount == 0:
            raise NotFoundError(f"No expense with id {expense_id}.")

    def totals_by_category(
        self, date_from: date | None = None, date_to: date | None = None
    ) -> list[CategoryTotal]:
        """Sum expenses per category within the inclusive date range, largest first."""
        clauses: list[str] = []
        params: list[str] = []
        if date_from is not None:
            clauses.append("e.spent_on >= ?")
            params.append(date_from.isoformat())
        if date_to is not None:
            clauses.append("e.spent_on <= ?")
            params.append(date_to.isoformat())
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        rows = self._conn.execute(
            "SELECT c.id AS category_id, c.name AS category, "
            "SUM(e.amount) AS total, COUNT(*) AS count "
            "FROM expenses AS e JOIN categories AS c ON c.id = e.category_id"
            f"{where} GROUP BY c.id ORDER BY total DESC, c.name",
            params,
        ).fetchall()
        return [
            CategoryTotal(
                category_id=int(row["category_id"]),
                category=str(row["category"]),
                total=int(row["total"]),
                count=int(row["count"]),
            )
            for row in rows
        ]

    def _require(self, expense_id: int) -> Expense:
        expense = self.get(expense_id)
        if expense is None:
            raise NotFoundError(f"No expense with id {expense_id}.")
        return expense


class BudgetRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def set(self, category_id: int, month: str, amount: int) -> Budget:
        """Create the budget for a category and month, or replace its amount."""
        with self._conn:
            self._conn.execute(
                "INSERT INTO budgets (category_id, month, amount) VALUES (?, ?, ?) "
                "ON CONFLICT (category_id, month) DO UPDATE SET amount = excluded.amount",
                (category_id, month, amount),
            )
        budget = self.get(category_id, month)
        assert budget is not None
        return budget

    def get(self, category_id: int, month: str) -> Budget | None:
        row = self._conn.execute(
            f"{_BUDGET_SELECT} WHERE b.category_id = ? AND b.month = ?", (category_id, month)
        ).fetchone()
        return _budget(row) if row else None

    def list_for_month(self, month: str) -> list[Budget]:
        rows = self._conn.execute(
            f"{_BUDGET_SELECT} WHERE b.month = ? ORDER BY c.name", (month,)
        ).fetchall()
        return [_budget(row) for row in rows]

    def remove(self, category_id: int, month: str) -> None:
        with self._conn:
            cursor = self._conn.execute(
                "DELETE FROM budgets WHERE category_id = ? AND month = ?", (category_id, month)
            )
        if cursor.rowcount == 0:
            raise NotFoundError(f"No budget set for that category in {month}.")
