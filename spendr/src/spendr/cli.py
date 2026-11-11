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
from spendr.formatting import describe_expense, expenses_table
from spendr.services import ExpenseService

app = typer.Typer(
    name="spendr",
    help="Track your expenses from the terminal.",
    no_args_is_help=True,
    add_completion=False,
    # User errors are reported as friendly messages, so never dump local variables.
    pretty_exceptions_show_locals=False,
)

console = Console()
err_console = Console(stderr=True)


@dataclass(frozen=True, slots=True)
class Session:
    """Everything a command needs: the user's settings and the services."""

    currency: str
    expenses: ExpenseService


@contextmanager
def session() -> Iterator[Session]:
    """Open the database for one command and turn expected errors into messages."""
    try:
        settings = config.load_config()
        with closing(db.connect(config.db_path())) as conn:
            yield Session(currency=settings.currency, expenses=ExpenseService(conn))
    except SpendrError as exc:
        err_console.print(f"[bold red]Error:[/] {escape(str(exc))}")
        raise typer.Exit(code=1) from None


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
