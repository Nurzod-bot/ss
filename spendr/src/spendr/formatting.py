"""Presentation helpers: money formatting and Rich renderables."""

from collections.abc import Sequence

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from spendr.models import BudgetReport, BudgetState, CategoryUsage, Expense, Summary

BAR_WIDTH = 30
BAR_COLORS = ("cyan", "magenta", "green", "yellow", "blue", "red")
METER_WIDTH = 10
STATE_STYLES = {
    BudgetState.OK: "green",
    BudgetState.WARNING: "red",
    BudgetState.OVER: "bold red",
}


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


def usage_meter(spent: int, budget: int, width: int = METER_WIDTH) -> str:
    """A fixed-width gauge, e.g. ``███████░░░``, that is full at or above budget."""
    filled = min(width, bar_length(spent, budget, width))
    return "█" * filled + "░" * (width - filled)


def budget_table(report: BudgetReport, currency: str) -> Table:
    """Spent versus budget for each budgeted category; red from 90% upwards."""
    lines = report.lines
    spent = sum(line.spent for line in lines)
    table = Table(
        title=f"Budgets for {report.month} ({currency})", header_style="bold", show_footer=True
    )
    table.add_column("Category", footer="Total", style="cyan")
    table.add_column(
        "Budget", footer=format_amount(report.category_budget_total), justify="right", no_wrap=True
    )
    table.add_column("Spent", footer=format_amount(spent), justify="right", no_wrap=True)
    table.add_column(
        "Remaining",
        footer=format_amount(report.category_budget_total - spent),
        justify="right",
        no_wrap=True,
    )
    table.add_column("Used", justify="right", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    for line in lines:
        style = STATE_STYLES[line.state]
        table.add_row(
            Text(line.category),
            format_amount(line.budget),
            format_amount(line.spent),
            Text(format_amount(line.remaining), style=style),
            Text(f"{usage_meter(line.spent, line.budget)} {line.percent_used:.0f}%", style=style),
            Text(line.state.value, style=style),
        )
    return table


def budget_highlights(report: BudgetReport, currency: str) -> Panel:
    """The headline figures of a month: savings, pace and anything that needs attention."""
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold", no_wrap=True)
    grid.add_column()

    def money(amount: int) -> str:
        return format_amount(amount, currency)

    limit, remaining, state = report.limit, report.remaining, report.state
    if limit is not None and remaining is not None and state is not None:
        label = "Overall budget" if report.overall_budget is not None else "Category budgets"
        grid.add_row(label, money(limit))
        share = report.total_spent * 100 / limit
        grid.add_row(
            "Spent", Text(f"{money(report.total_spent)} ({share:.0f}%)", style=STATE_STYLES[state])
        )
        if remaining < 0:
            grid.add_row("Over budget by", Text(money(-remaining), style="bold red"))
        else:
            grid.add_row(
                "Saved" if report.is_past else "Left to spend",
                Text(money(remaining), style="bold green"),
            )
    else:
        grid.add_row("Spent", money(report.total_spent))

    allowance = report.daily_allowance
    if allowance is not None and report.days_left:
        days = f"{report.days_left} day{'s' if report.days_left != 1 else ''}"
        grid.add_row("Daily allowance", f"{money(allowance)} per day for the next {days}")

    unallocated = report.unallocated
    if unallocated is not None and unallocated > 0 and report.lines:
        grid.add_row("Unallocated", f"{money(unallocated)} not assigned to any category")
    elif unallocated is not None and unallocated < 0:
        grid.add_row(
            "Over-allocated",
            Text(f"category budgets exceed the overall budget by {money(-unallocated)}", "yellow"),
        )

    if report.unbudgeted and report.lines:
        names = ", ".join(item.category for item in report.unbudgeted)
        grid.add_row(
            "Unbudgeted", Text(f"{money(report.unbudgeted_spent)} spent on {names}", "yellow")
        )

    over = [line.category for line in report.lines if line.state is BudgetState.OVER]
    near = [line.category for line in report.lines if line.state is BudgetState.WARNING]
    if over:
        grid.add_row("Over budget", Text(", ".join(over), style="bold red"))
    if near:
        grid.add_row("Above 90%", Text(", ".join(near), style="red"))

    if report.overall_budget is None:
        grid.add_row(
            "Tip", Text("set an overall limit with: spendr budget total AMOUNT", style="dim")
        )
    return Panel(grid, title="Highlights", title_align="left", expand=False)
