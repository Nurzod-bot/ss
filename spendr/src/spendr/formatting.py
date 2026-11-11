"""Presentation helpers: money formatting and Rich renderables."""

from collections.abc import Sequence

from rich.table import Table
from rich.text import Text

from spendr.models import Expense


def format_amount(amount: int, currency: str = "") -> str:
    """Format an integer amount with spaces as thousands separators.

    >>> format_amount(1250000, "UZS")
    '1 250 000 UZS'
    """
    number = f"{amount:,}".replace(",", " ")
    return f"{number} {currency}" if currency else number


def describe_expense(expense: Expense, currency: str) -> str:
    """One-line plain-text summary used in confirmation messages."""
    parts = [
        f"#{expense.id}",
        format_amount(expense.amount, currency),
        expense.category,
        expense.spent_on.isoformat(),
    ]
    if expense.note:
        parts.append(expense.note)
    return " · ".join(parts)


def expenses_table(expenses: Sequence[Expense], currency: str) -> Table:
    total = sum(expense.amount for expense in expenses)
    count = len(expenses)
    table = Table(
        title="Expenses",
        caption=f"{count} expense{'s' if count != 1 else ''} · "
        f"total {format_amount(total, currency)}",
        header_style="bold",
    )
    table.add_column("ID", justify="right", style="dim", no_wrap=True)
    table.add_column("Date", no_wrap=True)
    table.add_column("Category", style="cyan")
    table.add_column(f"Amount ({currency})", justify="right", no_wrap=True)
    table.add_column("Note")
    for expense in expenses:
        table.add_row(
            str(expense.id),
            expense.spent_on.isoformat(),
            # Text objects keep user input from being read as Rich markup.
            Text(expense.category),
            format_amount(expense.amount),
            Text(expense.note),
        )
    return table
