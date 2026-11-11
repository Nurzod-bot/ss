"""Plain data containers shared by every layer. No behaviour, no SQL."""

import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum, StrEnum


@dataclass(frozen=True, slots=True)
class Category:
    id: int
    name: str


@dataclass(frozen=True, slots=True)
class Expense:
    id: int
    amount: int
    """Amount in the smallest currency unit. Always a positive integer."""
    category_id: int
    category: str
    note: str
    spent_on: date
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Budget:
    id: int
    category_id: int
    category: str
    month: str
    """Calendar month as ``YYYY-MM``."""
    amount: int


@dataclass(frozen=True, slots=True)
class ExpenseFilter:
    """Criteria for listing expenses. Every field is optional; dates are inclusive."""

    category_id: int | None = None
    date_from: date | None = None
    date_to: date | None = None
    limit: int | None = None


@dataclass(frozen=True, slots=True)
class CategoryTotal:
    category_id: int
    category: str
    total: int
    count: int


@dataclass(frozen=True, slots=True)
class CategoryUsage:
    category: Category
    expense_count: int


@dataclass(frozen=True, slots=True)
class SummaryRow:
    category: str
    total: int
    count: int
    percent: float
    """Share of the grand total, 0-100."""


@dataclass(frozen=True, slots=True)
class Summary:
    month: str
    rows: list[SummaryRow]
    """One row per category with spending, largest first."""
    total: int
    count: int


WARNING_THRESHOLD_PERCENT = 90


class BudgetState(Enum):
    OK = "ok"
    WARNING = "near limit"
    OVER = "over budget"


def budget_state(spent: int, budget: int) -> BudgetState:
    """Classify spending against a limit, using integer maths only."""
    if spent > budget:
        return BudgetState.OVER
    if spent * 100 > budget * WARNING_THRESHOLD_PERCENT:
        return BudgetState.WARNING
    return BudgetState.OK


@dataclass(frozen=True, slots=True)
class BudgetLine:
    """Spending against the budget of one category."""

    category: str
    budget: int
    spent: int

    @property
    def remaining(self) -> int:
        """Money left; negative when over budget."""
        return self.budget - self.spent

    @property
    def percent_used(self) -> float:
        return self.spent * 100 / self.budget

    @property
    def state(self) -> BudgetState:
        return budget_state(self.spent, self.budget)


@dataclass(frozen=True, slots=True)
class BudgetReport:
    """Everything `spendr budget status` shows for one month."""

    month: str
    lines: list[BudgetLine]
    """Categories that have a budget, ordered by name."""
    unbudgeted: list[CategoryTotal]
    """Spending in categories without a budget, largest first."""
    overall_budget: int | None
    """The month's overall limit, if the user set one."""
    total_spent: int
    """All spending in the month, budgeted or not."""
    days_left: int | None
    """Days remaining including today; ``None`` unless this is the current month."""
    is_past: bool

    @property
    def category_budget_total(self) -> int:
        return sum(line.budget for line in self.lines)

    @property
    def unbudgeted_spent(self) -> int:
        return sum(item.total for item in self.unbudgeted)

    @property
    def limit(self) -> int | None:
        """The figure spending is judged against: the overall budget when set,
        otherwise the sum of the category budgets."""
        if self.overall_budget is not None:
            return self.overall_budget
        return self.category_budget_total or None

    @property
    def remaining(self) -> int | None:
        """Savings so far; negative when the month is over its limit."""
        return None if self.limit is None else self.limit - self.total_spent

    @property
    def state(self) -> BudgetState | None:
        return None if self.limit is None else budget_state(self.total_spent, self.limit)

    @property
    def unallocated(self) -> int | None:
        """Overall budget not assigned to any category; negative when the
        category budgets add up to more than the overall budget."""
        if self.overall_budget is None:
            return None
        return self.overall_budget - self.category_budget_total

    @property
    def daily_allowance(self) -> int | None:
        """What can still be spent per remaining day without exceeding the limit."""
        remaining = self.remaining
        if remaining is None or remaining <= 0 or not self.days_left:
            return None
        return remaining // self.days_left

    @property
    def is_empty(self) -> bool:
        return not self.lines and self.overall_budget is None


class Frequency(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


def add_months(start: date, months: int) -> date:
    """Shift a date by whole months, clamping to the month's last day.

    >>> add_months(date(2026, 1, 31), 1)
    datetime.date(2026, 2, 28)
    """
    index = start.year * 12 + (start.month - 1) + months
    year, month = divmod(index, 12)
    last_day = calendar.monthrange(year, month + 1)[1]
    return date(year, month + 1, min(start.day, last_day))


@dataclass(frozen=True, slots=True)
class RecurringExpense:
    """A template that becomes a real expense every time it falls due."""

    id: int
    amount: int
    category_id: int
    category: str
    note: str
    frequency: Frequency
    start_date: date
    end_date: date | None
    last_posted: date | None
    """Date of the most recent occurrence already recorded as an expense."""

    def occurrence(self, index: int) -> date:
        """The ``index``-th due date, counted from the start date.

        Always derived from the start date, so a rule that starts on the 31st
        returns to the 31st after a shorter month instead of drifting.
        """
        match self.frequency:
            case Frequency.DAILY:
                return self.start_date + timedelta(days=index)
            case Frequency.WEEKLY:
                return self.start_date + timedelta(weeks=index)
            case Frequency.MONTHLY:
                return add_months(self.start_date, index)
            case Frequency.YEARLY:
                return add_months(self.start_date, index * 12)

    def due_dates(self, until: date) -> list[date]:
        """Occurrences not yet recorded, up to and including ``until``."""
        limit = min(until, self.end_date) if self.end_date else until
        dates: list[date] = []
        index = 0
        while (due := self.occurrence(index)) <= limit:
            if self.last_posted is None or due > self.last_posted:
                dates.append(due)
            index += 1
        return dates

    @property
    def next_due(self) -> date | None:
        """The next occurrence still to be recorded; ``None`` once the rule has ended."""
        index = 0
        while True:
            due = self.occurrence(index)
            if self.end_date and due > self.end_date:
                return None
            if self.last_posted is None or due > self.last_posted:
                return due
            index += 1
