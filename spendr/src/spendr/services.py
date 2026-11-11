"""Business rules: input parsing, validation and the operations behind each command.

Nothing here prints or knows about the terminal, so it can be tested directly.
"""

import calendar
import re
import sqlite3
from datetime import date

from spendr.errors import CategoryInUseError, NotFoundError, ValidationError
from spendr.models import (
    Budget,
    BudgetLine,
    BudgetReport,
    Category,
    CategoryUsage,
    Expense,
    ExpenseFilter,
    Summary,
    SummaryRow,
)
from spendr.repository import BudgetRepository, CategoryRepository, ExpenseRepository

MAX_AMOUNT = 2**63 - 1  # largest integer SQLite can store
MAX_NOTE_LENGTH = 200
MAX_CATEGORY_LENGTH = 30

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


def current_month() -> str:
    return date.today().strftime("%Y-%m")


def clean_category_name(text: str) -> str:
    """Normalize a category name: trimmed, single-spaced and lower-case."""
    name = " ".join(text.split()).lower()
    if not name:
        raise ValidationError("Category name cannot be empty.")
    if len(name) > MAX_CATEGORY_LENGTH:
        raise ValidationError(f"Category name is too long (max {MAX_CATEGORY_LENGTH} characters).")
    if not all(ch.isalnum() or ch in " -_&" for ch in name):
        raise ValidationError(
            f"Invalid category name '{text}': use letters, digits, spaces, '-', '_' or '&'."
        )
    return name


def find_category(categories: CategoryRepository, name: str) -> Category:
    """Look a category up by name, with a helpful error when it does not exist."""
    category = categories.get_by_name(" ".join(name.split()).lower())
    if category is None:
        available = ", ".join(c.name for c in categories.list_all()) or "none yet"
        raise NotFoundError(
            f"Unknown category '{name}'. Available: {available}. "
            "Create one with: spendr category add NAME"
        )
    return category


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
        return find_category(self._categories, name)


class CategoryService:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._categories = CategoryRepository(conn)

    def usage(self) -> list[CategoryUsage]:
        return self._categories.usage()

    def add(self, name: str) -> Category:
        return self._categories.add(clean_category_name(name))

    def rename(self, old_name: str, new_name: str) -> Category:
        category = find_category(self._categories, old_name)
        cleaned = clean_category_name(new_name)
        if cleaned == category.name:
            raise ValidationError(f"Category is already named '{cleaned}'.")
        return self._categories.rename(category.id, cleaned)

    def remove(self, name: str) -> Category:
        """Delete an unused category (and its budgets) and return it."""
        category = find_category(self._categories, name)
        count = self._categories.expense_count(category.id)
        if count:
            raise CategoryInUseError(
                f"Category '{category.name}' still has {count} expense{'s' if count != 1 else ''}. "
                "Move them with `spendr edit ID --category NAME` or delete them first."
            )
        self._categories.remove(category.id)
        return category


class SummaryService:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._expenses = ExpenseRepository(conn)

    def for_month(self, month: str | None = None) -> Summary:
        """Total spending per category for a month (the current one by default)."""
        month = parse_month(month) if month is not None else current_month()
        totals = self._expenses.totals_by_category(*month_range(month))
        grand_total = sum(item.total for item in totals)
        rows = [
            SummaryRow(
                category=item.category,
                total=item.total,
                count=item.count,
                percent=item.total * 100 / grand_total,
            )
            for item in totals
        ]
        return Summary(
            month=month,
            rows=rows,
            total=grand_total,
            count=sum(item.count for item in totals),
        )


class BudgetService:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._budgets = BudgetRepository(conn)
        self._categories = CategoryRepository(conn)
        self._expenses = ExpenseRepository(conn)

    def set(
        self, category: str, amount: str, month: str | None = None
    ) -> tuple[Budget, int | None]:
        """Create or change a category budget. Returns it with the previous amount."""
        month = _month_or_current(month)
        category_id = find_category(self._categories, category).id
        new_amount = parse_amount(amount)
        previous = self._budgets.get(category_id, month)
        budget = self._budgets.set(category_id, month, new_amount)
        return budget, previous.amount if previous else None

    def remove(self, category: str, month: str | None = None) -> Budget:
        month = _month_or_current(month)
        found = find_category(self._categories, category)
        budget = self._budgets.get(found.id, month)
        if budget is None:
            raise NotFoundError(f"No budget set for '{found.name}' in {month}.")
        self._budgets.remove(found.id, month)
        return budget

    def set_total(self, amount: str, month: str | None = None) -> tuple[str, int, int | None]:
        """Create or change the overall monthly budget.

        Returns the month, the new amount and the previous amount.
        """
        month = _month_or_current(month)
        new_amount = parse_amount(amount)
        previous = self._budgets.get_total(month)
        self._budgets.set_total(month, new_amount)
        return month, new_amount, previous

    def remove_total(self, month: str | None = None) -> tuple[str, int]:
        month = _month_or_current(month)
        amount = self._budgets.get_total(month)
        if amount is None:
            raise NotFoundError(f"No overall budget set for {month}.")
        self._budgets.remove_total(month)
        return month, amount

    def status(self, month: str | None = None, today: date | None = None) -> BudgetReport:
        """Compare a month's spending with its category and overall budgets."""
        today = today or date.today()
        month = parse_month(month) if month is not None else today.strftime("%Y-%m")
        first_day, last_day = month_range(month)
        budgets = self._budgets.list_for_month(month)
        totals = self._expenses.totals_by_category(first_day, last_day)
        spent_by_category = {item.category_id: item.total for item in totals}
        budgeted_ids = {budget.category_id for budget in budgets}
        is_current = first_day <= today <= last_day
        return BudgetReport(
            month=month,
            lines=[
                BudgetLine(
                    category=budget.category,
                    budget=budget.amount,
                    spent=spent_by_category.get(budget.category_id, 0),
                )
                for budget in budgets
            ],
            unbudgeted=[item for item in totals if item.category_id not in budgeted_ids],
            overall_budget=self._budgets.get_total(month),
            total_spent=sum(item.total for item in totals),
            days_left=(last_day - today).days + 1 if is_current else None,
            is_past=last_day < today,
        )


def _month_or_current(month: str | None) -> str:
    return parse_month(month) if month is not None else current_month()
