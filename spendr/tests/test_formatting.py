from datetime import UTC, date, datetime
from io import StringIO

import pytest
from rich.console import Console

from spendr.formatting import describe_expense, expenses_table, format_amount
from spendr.models import Expense


def make_expense(expense_id: int = 1, amount: int = 45_000, note: str = "lunch plov") -> Expense:
    return Expense(
        id=expense_id,
        amount=amount,
        category_id=1,
        category="food",
        note=note,
        spent_on=date(2026, 11, 10),
        created_at=datetime(2026, 11, 10, tzinfo=UTC),
    )


def render(renderable: object) -> str:
    console = Console(file=StringIO(), width=120)
    console.print(renderable)
    assert isinstance(console.file, StringIO)
    return console.file.getvalue()


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (0, "0 UZS"),
        (999, "999 UZS"),
        (1_000, "1 000 UZS"),
        (45_000, "45 000 UZS"),
        (1_250_000, "1 250 000 UZS"),
        (-1_500, "-1 500 UZS"),
    ],
)
def test_format_amount(amount: int, expected: str) -> None:
    assert format_amount(amount, "UZS") == expected


def test_format_amount_without_currency() -> None:
    assert format_amount(1_250_000) == "1 250 000"


def test_describe_expense() -> None:
    assert (
        describe_expense(make_expense(), "UZS")
        == "#1 · 45 000 UZS · food · 2026-11-10 · lunch plov"
    )
    assert describe_expense(make_expense(note=""), "USD") == "#1 · 45 000 USD · food · 2026-11-10"


def test_expenses_table_shows_rows_and_total() -> None:
    output = render(expenses_table([make_expense(1), make_expense(2, 1_205_000, "rent")], "UZS"))

    assert "Amount (UZS)" in output
    assert "lunch plov" in output
    assert "1 205 000" in output
    assert "2 expenses · total 1 250 000 UZS" in output


def test_expenses_table_singular_caption() -> None:
    assert "1 expense · total 45 000 UZS" in render(expenses_table([make_expense()], "UZS"))


def test_expenses_table_does_not_interpret_markup_in_notes() -> None:
    output = render(expenses_table([make_expense(note="[red]sale[/red] [50%]")], "UZS"))

    assert "[red]sale[/red] [50%]" in output
