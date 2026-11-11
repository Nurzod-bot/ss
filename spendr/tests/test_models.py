import pytest

from spendr.models import BudgetLine, BudgetReport, BudgetState, CategoryTotal, budget_state


@pytest.mark.parametrize(
    ("spent", "budget", "expected"),
    [
        (0, 100, BudgetState.OK),
        (90, 100, BudgetState.OK),  # exactly 90% is not yet "over 90%"
        (91, 100, BudgetState.WARNING),
        (100, 100, BudgetState.WARNING),
        (101, 100, BudgetState.OVER),
        (901, 1000, BudgetState.WARNING),
        (9, 10, BudgetState.OK),
        (10, 10, BudgetState.WARNING),
    ],
)
def test_budget_state(spent: int, budget: int, expected: BudgetState) -> None:
    assert budget_state(spent, budget) is expected


def test_budget_line() -> None:
    line = BudgetLine(category="food", budget=200, spent=250)

    assert line.remaining == -50
    assert line.percent_used == 125.0
    assert line.state is BudgetState.OVER


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


class TestBudgetReport:
    def test_without_any_budget(self) -> None:
        report = make_report(total_spent=500)

        assert report.is_empty
        assert report.limit is None
        assert report.remaining is None
        assert report.state is None
        assert report.unallocated is None
        assert report.daily_allowance is None

    def test_limit_falls_back_to_category_budgets(self) -> None:
        report = make_report(
            lines=[BudgetLine("food", 300, 100), BudgetLine("housing", 700, 700)], total_spent=800
        )

        assert not report.is_empty
        assert report.category_budget_total == 1000
        assert report.limit == 1000
        assert report.remaining == 200
        assert report.state is BudgetState.OK
        assert report.unallocated is None

    def test_overall_budget_takes_precedence_and_may_differ(self) -> None:
        report = make_report(
            lines=[BudgetLine("food", 300, 100)],
            unbudgeted=[CategoryTotal(2, "transport", 50, 1), CategoryTotal(3, "health", 25, 2)],
            overall_budget=1000,
            total_spent=175,
        )

        assert report.limit == 1000
        assert report.remaining == 825
        assert report.unallocated == 700
        assert report.unbudgeted_spent == 75

    def test_over_allocated_and_over_budget(self) -> None:
        report = make_report(
            lines=[BudgetLine("food", 800, 900)], overall_budget=500, total_spent=900, days_left=3
        )

        assert report.unallocated == -300
        assert report.remaining == -400
        assert report.state is BudgetState.OVER
        assert report.daily_allowance is None

    @pytest.mark.parametrize(
        ("days_left", "expected"), [(10, 90), (1, 900), (7, 128), (None, None)]
    )
    def test_daily_allowance(self, days_left: int | None, expected: int | None) -> None:
        report = make_report(overall_budget=1000, total_spent=100, days_left=days_left)

        assert report.daily_allowance == expected
