from datetime import UTC, date, datetime
from io import StringIO

import pytest
from rich.console import Console

from spendr.formatting import (
    BAR_WIDTH,
    METER_WIDTH,
    bar_length,
    budget_highlights,
    budget_table,
    categories_table,
    describe_expense,
    describe_recurring,
    expenses_table,
    format_amount,
    format_percent,
    recurring_table,
    summary_chart,
    summary_table,
    usage_meter,
)
from spendr.models import (
    BudgetLine,
    BudgetReport,
    Category,
    CategoryTotal,
    CategoryUsage,
    Expense,
    Frequency,
    RecurringExpense,
    Summary,
    SummaryRow,
)

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


def make_report(
    *,
    lines: list[BudgetLine] | None = None,
    unbudgeted: list[CategoryTotal] | None = None,
    overall_budget: int | None = None,
    total_spent: int = 0,
    days_left: int | None = None,
    is_past: bool = False,
) -> BudgetReport:
    return BudgetReport(
        month="2026-11",
        lines=lines or [],
        unbudgeted=unbudgeted or [],
        overall_budget=overall_budget,
        total_spent=total_spent,
        days_left=days_left,
        is_past=is_past,
    )


def styled(renderable: object) -> str:
    """Render with colours on, so tests can check what is highlighted."""
    console = Console(file=StringIO(), width=120, force_terminal=True, color_system="standard")
    console.print(renderable)
    assert isinstance(console.file, StringIO)
    return console.file.getvalue()


RED = "\x1b[31m"
BOLD_RED = "\x1b[1;31m"
BOLD_GREEN = "\x1b[1;32m"


@pytest.mark.parametrize(
    ("spent", "budget", "filled"),
    [(0, 100, 0), (1, 100, 1), (50, 100, 5), (100, 100, 10), (250, 100, 10)],
)
def test_usage_meter(spent: int, budget: int, filled: int) -> None:
    meter = usage_meter(spent, budget)

    assert len(meter) == METER_WIDTH
    assert meter.count("█") == filled


def test_budget_table_rows_and_totals() -> None:
    report = make_report(
        lines=[BudgetLine("food", 1_500_000, 600_000), BudgetLine("housing", 1_200_000, 1_250_000)]
    )

    lines = render(budget_table(report, "UZS")).splitlines()

    assert "Budgets for 2026-11 (UZS)" in lines[0]
    food = next(line for line in lines if "food" in line)
    assert "1 500 000" in food and "600 000" in food and "900 000" in food and "40%" in food
    assert "ok" in food
    housing = next(line for line in lines if "housing" in line)
    assert "-50 000" in housing and "104%" in housing and "over budget" in housing
    total = next(line for line in lines if "Total" in line)
    assert "2 700 000" in total and "1 850 000" in total and "850 000" in total


def test_budget_table_warns_in_red_above_ninety_percent() -> None:
    report = make_report(
        lines=[
            BudgetLine("calm", 100, 90),
            BudgetLine("near", 100, 91),
            BudgetLine("over", 100, 101),
        ]
    )

    lines = styled(budget_table(report, "UZS")).splitlines()

    calm = next(line for line in lines if "calm" in line)
    near = next(line for line in lines if "near" in line)
    over = next(line for line in lines if "over" in line)
    assert RED not in calm and BOLD_RED not in calm
    assert RED in near
    assert BOLD_RED in over


class TestBudgetHighlights:
    def test_savings_and_daily_allowance_in_current_month(self) -> None:
        report = make_report(
            lines=[BudgetLine("food", 300_000, 100_000)],
            overall_budget=1_000_000,
            total_spent=100_000,
            days_left=20,
        )

        output = render(budget_highlights(report, "UZS"))

        assert "Overall budget" in output and "1 000 000 UZS" in output
        assert "100 000 UZS (10%)" in output
        assert "Left to spend" in output and "900 000 UZS" in output
        assert "45 000 UZS per day for the next 20 days" in output
        assert "700 000 UZS not assigned to any category" in output
        assert "Tip" not in output
        assert BOLD_GREEN in styled(budget_highlights(report, "UZS"))

    def test_past_month_shows_saved(self) -> None:
        report = make_report(overall_budget=1000, total_spent=400, is_past=True)

        output = render(budget_highlights(report, "UZS"))

        assert "Saved" in output and "600 UZS" in output
        assert "Daily allowance" not in output

    def test_single_day_left(self) -> None:
        report = make_report(overall_budget=1000, total_spent=400, days_left=1)

        assert "per day for the next 1 day " in render(budget_highlights(report, "UZS")) + " "

    def test_over_budget_is_highlighted_in_red(self) -> None:
        report = make_report(
            lines=[BudgetLine("food", 800, 900), BudgetLine("fun", 100, 95)],
            unbudgeted=[CategoryTotal(3, "transport", 70, 1)],
            overall_budget=500,
            total_spent=1065,
            days_left=5,
        )

        output = render(budget_highlights(report, "UZS"))

        assert "Over budget by" in output and "565 UZS" in output
        assert "Left to spend" not in output
        assert "Daily allowance" not in output
        assert "category budgets exceed the overall budget by 400 UZS" in output
        assert "70 UZS spent on transport" in output
        assert "Above 90%" in output
        assert BOLD_RED in styled(budget_highlights(report, "UZS"))

    def test_without_overall_budget_uses_category_budgets_and_gives_tip(self) -> None:
        report = make_report(lines=[BudgetLine("food", 1000, 250)], total_spent=250)

        output = render(budget_highlights(report, "UZS"))

        assert "Category budgets" in output
        assert "750 UZS" in output
        assert "Unallocated" not in output
        assert "spendr budget total AMOUNT" in output

    def test_without_any_budget_only_reports_spending(self) -> None:
        output = render(budget_highlights(make_report(total_spent=1234), "UZS"))

        assert "1 234 UZS" in output
        assert "Left to spend" not in output


def make_rule(**changes: object) -> RecurringExpense:
    values: dict[str, object] = {
        "id": 1,
        "amount": 1_250_000,
        "category_id": 1,
        "category": "housing",
        "note": "rent",
        "frequency": Frequency.MONTHLY,
        "start_date": date(2026, 11, 1),
        "end_date": None,
        "last_posted": date(2026, 11, 1),
    }
    return RecurringExpense(**{**values, **changes})  # type: ignore[arg-type]


def test_describe_recurring() -> None:
    assert describe_recurring(make_rule(), "UZS") == "#1 · 1 250 000 UZS · housing · monthly · rent"
    assert describe_recurring(make_rule(note=""), "UZS") == "#1 · 1 250 000 UZS · housing · monthly"


def test_recurring_table() -> None:
    ended = make_rule(id=2, note="[gym]", frequency=Frequency.YEARLY, end_date=date(2026, 11, 1))

    lines = render(recurring_table([make_rule(), ended], "UZS")).splitlines()

    active = next(line for line in lines if "rent" in line)
    assert "1 250 000" in active and "monthly" in active
    assert "2026-12-01" in active and "never" in active
    finished = next(line for line in lines if "[gym]" in line)
    assert "yearly" in finished and "ended" in finished and "2026-11-01" in finished
