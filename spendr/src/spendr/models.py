"""Plain data containers shared by every layer. No behaviour, no SQL."""

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


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
