"""Business rules: input parsing, validation and the operations behind each command.

Nothing here prints or knows about the terminal, so it can be tested directly.
"""

import calendar
import re
import sqlite3
from datetime import date

from spendr.errors import NotFoundError, ValidationError
from spendr.models import Category, Expense, ExpenseFilter
from spendr.repository import CategoryRepository, ExpenseRepository

MAX_AMOUNT = 2**63 - 1  # largest integer SQLite can store
MAX_NOTE_LENGTH = 200

_AMOUNT_RE = re.compile(r"[+-]?[0-9]+")
_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_MONTH_RE = re.compile(r"([0-9]{4})-([0-9]{2})")


def parse_amount(text: str) -> int:
    """Parse a positive whole amount. Spaces and underscores may group digits."""
    cleaned = text.strip().replace(" ", "").replace("_", "")
    if not _AMOUNT_RE.fullmatch(cleaned):
        raise ValidationError(
            f"Invalid amount '{text}': use a whole number without decimals, e.g. 45000."
        )
    amount = int(cleaned)
    if amount <= 0:
        raise ValidationError("Amount must be greater than zero.")
    if amount > MAX_AMOUNT:
        raise ValidationError("Amount is too large.")
    return amount


def parse_date(text: str) -> date:
    """Parse a ``YYYY-MM-DD`` calendar date."""
    cleaned = text.strip()
    try:
        if not _DATE_RE.fullmatch(cleaned):
            raise ValueError
        return date.fromisoformat(cleaned)
    except ValueError:
        raise ValidationError(
            f"Invalid date '{text}': use YYYY-MM-DD with a real calendar day, e.g. 2026-11-10."
        ) from None


def parse_month(text: str) -> str:
    """Validate a ``YYYY-MM`` month and return it in canonical form."""
    match = _MONTH_RE.fullmatch(text.strip())
    if not match or not 1 <= int(match[2]) <= 12 or int(match[1]) == 0:
        raise ValidationError(f"Invalid month '{text}': use YYYY-MM, e.g. 2026-11.")
    return match[0]


def month_range(month: str) -> tuple[date, date]:
    """Return the first and last day of a ``YYYY-MM`` month."""
    year, month_number = (int(part) for part in parse_month(month).split("-"))
    last_day = calendar.monthrange(year, month_number)[1]
    return date(year, month_number, 1), date(year, month_number, last_day)


def clean_note(text: str) -> str:
    note = " ".join(text.split())
    if len(note) > MAX_NOTE_LENGTH:
        raise ValidationError(f"Note is too long (max {MAX_NOTE_LENGTH} characters).")
    return note


def resolve_date_range(
    date_from: str | None, date_to: str | None, month: str | None
) -> tuple[date | None, date | None]:
    """Turn the ``--from`` / ``--to`` / ``--month`` options into an inclusive range."""
    if month is not None:
        if date_from is not None or date_to is not None:
            raise ValidationError("Use either --month or --from/--to, not both.")
        return month_range(month)
    start = parse_date(date_from) if date_from is not None else None
    end = parse_date(date_to) if date_to is not None else None
    if start and end and start > end:
        raise ValidationError(f"--from ({start}) must not be after --to ({end}).")
    return start, end


class ExpenseService:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._expenses = ExpenseRepository(conn)
        self._categories = CategoryRepository(conn)

    def add(
        self, amount: str, category: str, note: str = "", spent_on: str | None = None
    ) -> Expense:
        return self._expenses.add(
            amount=parse_amount(amount),
            category_id=self._category(category).id,
            note=clean_note(note),
            spent_on=parse_date(spent_on) if spent_on is not None else date.today(),
        )

    def get(self, expense_id: int) -> Expense:
        expense = self._expenses.get(expense_id)
        if expense is None:
            raise NotFoundError(f"No expense with id {expense_id}.")
        return expense

    def find(
        self,
        *,
        category: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        month: str | None = None,
        limit: int | None = None,
    ) -> list[Expense]:
        if limit is not None and limit < 1:
            raise ValidationError("--limit must be at least 1.")
        start, end = resolve_date_range(date_from, date_to, month)
        return self._expenses.find(
            ExpenseFilter(
                category_id=self._category(category).id if category is not None else None,
                date_from=start,
                date_to=end,
                limit=limit,
            )
        )

    def edit(
        self,
        expense_id: int,
        *,
        amount: str | None = None,
        category: str | None = None,
        note: str | None = None,
        spent_on: str | None = None,
    ) -> Expense:
        if amount is None and category is None and note is None and spent_on is None:
            raise ValidationError(
                "Nothing to change. Pass at least one of --amount, --category, --note or --date."
            )
        self.get(expense_id)  # report a missing id before any other problem
        return self._expenses.update(
            expense_id,
            amount=parse_amount(amount) if amount is not None else None,
            category_id=self._category(category).id if category is not None else None,
            note=clean_note(note) if note is not None else None,
            spent_on=parse_date(spent_on) if spent_on is not None else None,
        )

    def delete(self, expense_id: int) -> Expense:
        """Delete an expense and return what was removed."""
        expense = self.get(expense_id)
        self._expenses.delete(expense_id)
        return expense

    def _category(self, name: str) -> Category:
        category = self._categories.get_by_name(name.strip())
        if category is None:
            available = ", ".join(c.name for c in self._categories.list_all()) or "none yet"
            raise NotFoundError(f"Unknown category '{name}'. Available: {available}.")
        return category
