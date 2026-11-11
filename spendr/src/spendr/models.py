"""Plain data containers shared by every layer. No behaviour, no SQL."""

from dataclasses import dataclass
from datetime import date, datetime


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
