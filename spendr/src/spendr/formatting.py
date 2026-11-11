"""Presentation helpers: money formatting and Rich renderables."""

from collections.abc import Sequence

from rich.table import Table
from rich.text import Text

from spendr.models import CategoryUsage, Expense, Summary

BAR_WIDTH = 30
BAR_COLORS = ("cyan", "magenta", "green", "yellow", "blue", "red")


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


def format_percent(percent: float) -> str:
    return f"{percent:.1f}%"


def categories_table(usage: Sequence[CategoryUsage]) -> Table:
    table = Table(title="Categories", header_style="bold")
    table.add_column("Category", style="cyan")
    table.add_column("Expenses", justify="right")
    for item in usage:
        table.add_row(Text(item.category.name), str(item.expense_count))
    return table


def summary_table(summary: Summary, currency: str) -> Table:
    table = Table(title=f"Summary for {summary.month}", header_style="bold", show_footer=True)
    table.add_column("Category", footer="Total", style="cyan")
    table.add_column("Expenses", footer=str(summary.count), justify="right")
    table.add_column(
        f"Amount ({currency})", footer=format_amount(summary.total), justify="right", no_wrap=True
    )
    table.add_column("Share", footer=format_percent(100), justify="right", no_wrap=True)
    for row in summary.rows:
        table.add_row(
            Text(row.category),
            str(row.count),
            format_amount(row.total),
            format_percent(row.percent),
        )
    return table


def bar_length(value: int, largest: int, width: int = BAR_WIDTH) -> int:
    """Scale ``value`` to a bar where ``largest`` fills ``width`` cells.

    Any non-zero value gets at least one cell so small categories stay visible.
    """
    if value <= 0 or largest <= 0:
        return 0
    return max(1, round(value * width / largest))


def summary_chart(summary: Summary) -> Table:
    """Horizontal bar chart of spending per category, scaled to the largest one."""
    largest = max((row.total for row in summary.rows), default=0)
    chart = Table.grid(padding=(0, 1))
    chart.add_column(justify="right", style="cyan")
    chart.add_column(no_wrap=True)
    chart.add_column(justify="right", no_wrap=True)
    for index, row in enumerate(summary.rows):
        bar = Text("█" * bar_length(row.total, largest), style=BAR_COLORS[index % len(BAR_COLORS)])
        chart.add_row(Text(row.category), bar, format_percent(row.percent))
    return chart
