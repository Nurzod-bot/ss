from datetime import UTC, date, datetime
from io import StringIO

import pytest
from rich.console import Console

from spendr.formatting import (
    BAR_WIDTH,
    bar_length,
    categories_table,
    describe_expense,
    expenses_table,
    format_amount,
    format_percent,
    summary_chart,
    summary_table,
)
from spendr.models import Category, CategoryUsage, Expense, Summary, SummaryRow

SUMMARY = Summary(
    month="2026-11",
    rows=[
        SummaryRow(category="housing", total=1_250_000, count=1, percent=87.9),
        SummaryRow(category="food", total=165_000, count=2, percent=11.6),
        SummaryRow(category="transport", total=7_000, count=1, percent=0.5),
    ],
    total=1_422_000,
    count=4,
)


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


@pytest.mark.parametrize(
    ("percent", "expected"), [(0, "0.0%"), (11.649, "11.6%"), (87.95, "88.0%"), (100, "100.0%")]
)
def test_format_percent(percent: float, expected: str) -> None:
    assert format_percent(percent) == expected


def test_categories_table() -> None:
    output = render(categories_table([CategoryUsage(Category(1, "food"), 12)]))

    assert "food" in output
    assert "12" in output


def test_summary_table_shows_rows_and_grand_total() -> None:
    lines = render(summary_table(SUMMARY, "UZS")).splitlines()

    assert "Summary for 2026-11" in lines[0]
    housing = next(line for line in lines if "housing" in line)
    assert "1 250 000" in housing
    assert "87.9%" in housing
    total = next(line for line in lines if "Total" in line)
    assert "1 422 000" in total
    assert "100.0%" in total


@pytest.mark.parametrize(
    ("value", "largest", "expected"),
    [(100, 100, BAR_WIDTH), (50, 100, BAR_WIDTH // 2), (1, 1_000_000, 1), (0, 100, 0), (0, 0, 0)],
)
def test_bar_length(value: int, largest: int, expected: int) -> None:
    assert bar_length(value, largest) == expected


def test_summary_chart_scales_bars_to_largest_category() -> None:
    lines = render(summary_chart(SUMMARY)).splitlines()

    bars = {line.split()[0]: line.count("█") for line in lines}
    assert bars == {"housing": BAR_WIDTH, "food": 4, "transport": 1}
    assert "87.9%" in lines[0]


def test_summary_chart_of_empty_summary_renders_nothing() -> None:
    empty = Summary(month="2026-11", rows=[], total=0, count=0)

    assert render(summary_chart(empty)).strip() == ""
