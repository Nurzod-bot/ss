"""Typer commands. This module only parses input and renders output;
business logic lives in :mod:`spendr.services`."""

from collections.abc import Iterator
from contextlib import closing, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markup import escape

from spendr import __version__, config, db
from spendr.errors import SpendrError
from spendr.formatting import (
    budget_highlights,
    budget_table,
    categories_table,
    describe_expense,
    expenses_table,
    format_amount,
    summary_chart,
    summary_table,
)
from spendr.services import BudgetService, CategoryService, ExpenseService, SummaryService
from spendr.transfer import ExportFormat, TransferService, write_text

app = typer.Typer(
    name="spendr",
    help="Track your expenses from the terminal.",
    no_args_is_help=True,
    add_completion=False,
    # User errors are reported as friendly messages, so never dump local variables.
    pretty_exceptions_show_locals=False,
)

category_app = typer.Typer(help="Manage expense categories.", no_args_is_help=True)
budget_app = typer.Typer(help="Set budgets and track spending against them.", no_args_is_help=True)
config_app = typer.Typer(help="Show or change settings.", no_args_is_help=True)
app.add_typer(category_app, name="category")
app.add_typer(budget_app, name="budget")
app.add_typer(config_app, name="config")

# Automatic highlighting would colour digits and paths inconsistently; all styling is explicit.
console = Console(highlight=False)
err_console = Console(stderr=True, highlight=False)


@dataclass(frozen=True, slots=True)
class Session:
    """Everything a command needs: the user's settings and the services."""

    currency: str
    expenses: ExpenseService
    categories: CategoryService
    summaries: SummaryService
    budgets: BudgetService
    transfer: TransferService


@contextmanager
def friendly_errors() -> Iterator[None]:
    """Report expected errors as a one-line message instead of a traceback."""
    try:
        yield
    except SpendrError as exc:
        # soft_wrap keeps long file paths in one piece so they stay copyable.
        err_console.print(f"[bold red]Error:[/] {escape(str(exc))}", soft_wrap=True)
        raise typer.Exit(code=1) from None


@contextmanager
def session() -> Iterator[Session]:
    """Load settings and open the database for the duration of one command."""
    with friendly_errors():
        settings = config.load_config()
        with closing(db.connect(config.db_path())) as conn:
            yield Session(
                currency=settings.currency,
                expenses=ExpenseService(conn),
                categories=CategoryService(conn),
                summaries=SummaryService(conn),
                budgets=BudgetService(conn),
                transfer=TransferService(conn),
            )


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"spendr {__version__}")
        raise typer.Exit


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            help="Show the version and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """Track your expenses from the terminal."""


# ``ignore_unknown_options`` lets a negative amount reach our own validation
# instead of being rejected by the option parser as an unknown flag.
@app.command(context_settings={"ignore_unknown_options": True})
def add(
    amount: Annotated[str, typer.Argument(help="Whole amount, e.g. 45000.")],
    category: Annotated[str, typer.Argument(help="Category name, e.g. food.")],
    note: Annotated[str, typer.Argument(help="Optional description.")] = "",
    spent_on: Annotated[
        str | None,
        typer.Option("--date", "-d", metavar="YYYY-MM-DD", help="Date spent. Defaults to today."),
    ] = None,
) -> None:
    """Record a new expense."""
    with session() as s:
        expense = s.expenses.add(amount, category, note, spent_on)
        console.print(f"[green]Added[/] {escape(describe_expense(expense, s.currency))}")


@app.command("list")
def list_expenses(
    category: Annotated[
        str | None, typer.Option("--category", "-c", help="Only this category.")
    ] = None,
    date_from: Annotated[
        str | None, typer.Option("--from", metavar="YYYY-MM-DD", help="On or after this date.")
    ] = None,
    date_to: Annotated[
        str | None, typer.Option("--to", metavar="YYYY-MM-DD", help="On or before this date.")
    ] = None,
    month: Annotated[
        str | None, typer.Option("--month", "-m", metavar="YYYY-MM", help="Only this month.")
    ] = None,
    limit: Annotated[
        int | None, typer.Option("--limit", "-n", help="Show at most this many, newest first.")
    ] = None,
) -> None:
    """Show expenses, newest first."""
    with session() as s:
        expenses = s.expenses.find(
            category=category, date_from=date_from, date_to=date_to, month=month, limit=limit
        )
        if not expenses:
            console.print("No expenses found.")
            return
        console.print(expenses_table(expenses, s.currency))


@app.command()
def edit(
    expense_id: Annotated[int, typer.Argument(metavar="ID", help="Id shown by `spendr list`.")],
    amount: Annotated[str | None, typer.Option("--amount", "-a", help="New amount.")] = None,
    category: Annotated[str | None, typer.Option("--category", "-c", help="New category.")] = None,
    note: Annotated[
        str | None, typer.Option("--note", "-n", help='New note. Pass "" to clear it.')
    ] = None,
    spent_on: Annotated[
        str | None, typer.Option("--date", "-d", metavar="YYYY-MM-DD", help="New date.")
    ] = None,
) -> None:
    """Change one or more fields of an expense."""
    with session() as s:
        expense = s.expenses.edit(
            expense_id, amount=amount, category=category, note=note, spent_on=spent_on
        )
        console.print(f"[green]Updated[/] {escape(describe_expense(expense, s.currency))}")


@app.command()
def delete(
    expense_id: Annotated[int, typer.Argument(metavar="ID", help="Id shown by `spendr list`.")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip the confirmation.")] = False,
) -> None:
    """Delete an expense."""
    with session() as s:
        summary = describe_expense(s.expenses.get(expense_id), s.currency)
        if not yes and not typer.confirm(f"Delete {summary}?"):
            console.print("Cancelled.")
            return
        s.expenses.delete(expense_id)
        console.print(f"[green]Deleted[/] {escape(summary)}")


@app.command()
def summary(
    month: Annotated[
        str | None,
        typer.Option("--month", "-m", metavar="YYYY-MM", help="Defaults to the current month."),
    ] = None,
) -> None:
    """Show spending per category for a month."""
    with session() as s:
        result = s.summaries.for_month(month)
        if not result.rows:
            console.print(f"No expenses in {result.month}.")
            return
        console.print(summary_table(result, s.currency))
        console.print()
        console.print(summary_chart(result))


@app.command()
def export(
    fmt: Annotated[
        ExportFormat, typer.Option("--format", "-f", help="File format.")
    ] = ExportFormat.CSV,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="File to write. Prints to the terminal if omitted."),
    ] = None,
    force: Annotated[bool, typer.Option("--force", help="Overwrite an existing file.")] = False,
    category: Annotated[
        str | None, typer.Option("--category", "-c", help="Only this category.")
    ] = None,
    date_from: Annotated[
        str | None, typer.Option("--from", metavar="YYYY-MM-DD", help="On or after this date.")
    ] = None,
    date_to: Annotated[
        str | None, typer.Option("--to", metavar="YYYY-MM-DD", help="On or before this date.")
    ] = None,
    month: Annotated[
        str | None, typer.Option("--month", "-m", metavar="YYYY-MM", help="Only this month.")
    ] = None,
) -> None:
    """Export expenses to CSV or JSON, oldest first."""
    with session() as s:
        text, count = s.transfer.export(
            fmt, category=category, date_from=date_from, date_to=date_to, month=month
        )
        if output is None:
            typer.echo(text, nl=False)
            return
        write_text(output, text, overwrite=force)
        console.print(
            f"[green]Exported[/] {count} expense{'s' if count != 1 else ''} "
            f"to {escape(str(output))}",
            soft_wrap=True,
        )


@app.command("import")
def import_expenses(
    file: Annotated[
        Path, typer.Argument(help="CSV file with date, category, amount and optional note.")
    ],
    create_categories: Annotated[
        bool, typer.Option("--create-categories", help="Add categories that do not exist yet.")
    ] = False,
    skip_duplicates: Annotated[
        bool,
        typer.Option("--skip-duplicates", help="Skip rows identical to an existing expense."),
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Check the file without importing anything.")
    ] = False,
) -> None:
    """Import expenses from a CSV file. Nothing is imported if any row is invalid."""
    with session() as s:
        result = s.transfer.import_csv(
            file,
            create_categories=create_categories,
            skip_duplicates=skip_duplicates,
            dry_run=dry_run,
        )
        plural = "s" if result.imported != 1 else ""
        if result.dry_run:
            message = f"[yellow]Dry run:[/] {result.imported} expense{plural} would be imported"
        else:
            message = f"[green]Imported[/] {result.imported} expense{plural}"
        details = []
        if result.skipped_duplicates:
            details.append(f"{result.skipped_duplicates} duplicates skipped")
        if result.created_categories:
            verb = "would create" if result.dry_run else "created"
            names = ", ".join(result.created_categories)
            details.append(f"{verb} categories: {escape(names)}")
        if details:
            message += f" ({'; '.join(details)})"
        console.print(message)


@category_app.command("list")
def category_list() -> None:
    """Show all categories and how many expenses each has."""
    with session() as s:
        usage = s.categories.usage()
        if not usage:
            console.print("No categories yet. Create one with: spendr category add NAME")
            return
        console.print(categories_table(usage))


@category_app.command("add")
def category_add(name: Annotated[str, typer.Argument(help="Name of the new category.")]) -> None:
    """Create a category."""
    with session() as s:
        category = s.categories.add(name)
        console.print(f"[green]Added[/] category '{escape(category.name)}'")


@category_app.command("rename")
def category_rename(
    old_name: Annotated[str, typer.Argument(metavar="OLD", help="Current name.")],
    new_name: Annotated[str, typer.Argument(metavar="NEW", help="New name.")],
) -> None:
    """Rename a category. Its expenses and budgets follow along."""
    with session() as s:
        category = s.categories.rename(old_name, new_name)
        console.print(f"[green]Renamed[/] category to '{escape(category.name)}'")


@category_app.command("remove")
def category_remove(
    name: Annotated[str, typer.Argument(help="Category to remove.")],
) -> None:
    """Remove a category that has no expenses. Its budgets are removed too."""
    with session() as s:
        category = s.categories.remove(name)
        console.print(f"[green]Removed[/] category '{escape(category.name)}'")


MonthOption = Annotated[
    str | None,
    typer.Option("--month", "-m", metavar="YYYY-MM", help="Defaults to the current month."),
]


def _changed(label: str, amount: int, previous: int | None, currency: str) -> str:
    """Message for a budget that was created, changed or left as it was."""
    new = format_amount(amount, currency)
    if previous is None:
        return f"[green]Set[/] {label} to {new}"
    if previous == amount:
        return f"{label[0].upper()}{label[1:]} is already {new}"
    return f"[green]Changed[/] {label} from {format_amount(previous, currency)} to {new}"


@budget_app.command("set", context_settings={"ignore_unknown_options": True})
def budget_set(
    category: Annotated[str, typer.Argument(help="Category to budget for.")],
    amount: Annotated[str, typer.Argument(help="Limit for the month, e.g. 1500000.")],
    month: MonthOption = None,
) -> None:
    """Set a category's budget for a month. Run it again to change the amount."""
    with session() as s:
        budget, previous = s.budgets.set(category, amount, month)
        label = f"{escape(budget.category)} budget for {budget.month}"
        console.print(_changed(label, budget.amount, previous, s.currency))


@budget_app.command("total", context_settings={"ignore_unknown_options": True})
def budget_total(
    amount: Annotated[str, typer.Argument(help="Overall limit for the month, e.g. 5000000.")],
    month: MonthOption = None,
) -> None:
    """Set the overall budget for a month, independent of the category budgets."""
    with session() as s:
        target, new_amount, previous = s.budgets.set_total(amount, month)
        console.print(_changed(f"overall budget for {target}", new_amount, previous, s.currency))


@budget_app.command("remove")
def budget_remove(
    category: Annotated[
        str | None, typer.Argument(help="Category whose budget to remove.", show_default=False)
    ] = None,
    total: Annotated[
        bool, typer.Option("--total", help="Remove the overall budget instead.")
    ] = False,
    month: MonthOption = None,
) -> None:
    """Remove a category budget, or the overall budget with --total."""
    with session() as s:
        if total == (category is not None):
            err_console.print("[bold red]Error:[/] Give either a category or --total.")
            raise typer.Exit(code=1)
        if category is not None:
            budget = s.budgets.remove(category, month)
            what = f"{escape(budget.category)} budget for {budget.month}"
            amount = budget.amount
        else:
            target, amount = s.budgets.remove_total(month)
            what = f"overall budget for {target}"
        console.print(f"[green]Removed[/] {what} ({format_amount(amount, s.currency)})")


@budget_app.command("status")
def budget_status(month: MonthOption = None) -> None:
    """Show spent versus budget, with savings and warnings highlighted."""
    with session() as s:
        report = s.budgets.status(month)
        if report.is_empty:
            console.print(
                f"No budgets set for {report.month}. Start with:\n"
                "  spendr budget set CATEGORY AMOUNT\n"
                "  spendr budget total AMOUNT",
            )
            return
        if report.lines:
            console.print(budget_table(report, s.currency))
        console.print(budget_highlights(report, s.currency))


@config_app.command("show")
def config_show() -> None:
    """Show the current settings and where spendr keeps its files."""
    with friendly_errors():
        settings = config.load_config()
    console.print(f"Currency:    {escape(settings.currency)}", soft_wrap=True)
    console.print(f"Config file: {escape(str(config.config_path()))}", soft_wrap=True)
    console.print(f"Database:    {escape(str(config.db_path()))}", soft_wrap=True)


@config_app.command("currency")
def config_currency(
    code: Annotated[str, typer.Argument(help="Currency code shown next to amounts, e.g. USD.")],
) -> None:
    """Set the default currency."""
    with friendly_errors():
        settings = config.Config(currency=config.normalize_currency(code))
        config.save_config(settings)
    console.print(f"[green]Currency set to[/] {escape(settings.currency)}")
