"""Typer commands. This module only parses input and renders output;
business logic lives in :mod:`spendr.services`."""

from collections.abc import Iterator
from contextlib import closing, contextmanager
from dataclasses import dataclass
from typing import Annotated

import typer
from rich.console import Console
from rich.markup import escape

from spendr import __version__, config, db
from spendr.errors import SpendrError
from spendr.formatting import (
    categories_table,
    describe_expense,
    expenses_table,
    summary_chart,
    summary_table,
)
from spendr.services import CategoryService, ExpenseService, SummaryService

app = typer.Typer(
    name="spendr",
    help="Track your expenses from the terminal.",
    no_args_is_help=True,
    add_completion=False,
    # User errors are reported as friendly messages, so never dump local variables.
    pretty_exceptions_show_locals=False,
)

category_app = typer.Typer(help="Manage expense categories.", no_args_is_help=True)
config_app = typer.Typer(help="Show or change settings.", no_args_is_help=True)
app.add_typer(category_app, name="category")
app.add_typer(config_app, name="config")

console = Console()
err_console = Console(stderr=True)


@dataclass(frozen=True, slots=True)
class Session:
    """Everything a command needs: the user's settings and the services."""

    currency: str
    expenses: ExpenseService
    categories: CategoryService
    summaries: SummaryService


@contextmanager
def friendly_errors() -> Iterator[None]:
    """Report expected errors as a one-line message instead of a traceback."""
    try:
        yield
    except SpendrError as exc:
        err_console.print(f"[bold red]Error:[/] {escape(str(exc))}")
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


@config_app.command("show")
def config_show() -> None:
    """Show the current settings and where spendr keeps its files."""
    with friendly_errors():
        settings = config.load_config()
    console.print(f"Currency:    {escape(settings.currency)}", highlight=False, soft_wrap=True)
    console.print(
        f"Config file: {escape(str(config.config_path()))}", highlight=False, soft_wrap=True
    )
    console.print(f"Database:    {escape(str(config.db_path()))}", highlight=False, soft_wrap=True)


@config_app.command("currency")
def config_currency(
    code: Annotated[str, typer.Argument(help="Currency code shown next to amounts, e.g. USD.")],
) -> None:
    """Set the default currency."""
    with friendly_errors():
        settings = config.Config(currency=config.normalize_currency(code))
        config.save_config(settings)
    console.print(f"[green]Currency set to[/] {escape(settings.currency)}")
