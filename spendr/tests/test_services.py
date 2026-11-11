import sqlite3
from datetime import date

import pytest

from spendr import db, services
from spendr.errors import CategoryInUseError, DuplicateError, NotFoundError, ValidationError
from spendr.models import BudgetState
from spendr.services import BudgetService, CategoryService, ExpenseService, SummaryService

NOV_11 = date(2026, 11, 11)


@pytest.fixture
def service(conn: sqlite3.Connection) -> ExpenseService:
    return ExpenseService(conn)


@pytest.fixture
def categories(conn: sqlite3.Connection) -> CategoryService:
    return CategoryService(conn)


@pytest.fixture
def summaries(conn: sqlite3.Connection) -> SummaryService:
    return SummaryService(conn)


@pytest.fixture
def budgets(conn: sqlite3.Connection) -> BudgetService:
    return BudgetService(conn)


class TestParseAmount:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [("45000", 45_000), (" 1 250 000 ", 1_250_000), ("1_000", 1_000), ("+7", 7), ("007", 7)],
    )
    def test_valid(self, text: str, expected: int) -> None:
        assert services.parse_amount(text) == expected

    @pytest.mark.parametrize("text", ["", "abc", "12.5", "12,5", "1e3", "١٢", "--5", "5-"])
    def test_malformed(self, text: str) -> None:
        with pytest.raises(ValidationError, match="Invalid amount"):
            services.parse_amount(text)

    @pytest.mark.parametrize("text", ["0", "-1", "-45000"])
    def test_not_positive(self, text: str) -> None:
        with pytest.raises(ValidationError, match="greater than zero"):
            services.parse_amount(text)

    def test_too_large(self) -> None:
        assert services.parse_amount(str(services.MAX_AMOUNT)) == services.MAX_AMOUNT
        with pytest.raises(ValidationError, match="too large"):
            services.parse_amount(str(services.MAX_AMOUNT + 1))


class TestParseDate:
    def test_valid(self) -> None:
        assert services.parse_date(" 2024-02-29 ") == date(2024, 2, 29)

    @pytest.mark.parametrize(
        "text", ["", "today", "2026-02-30", "2025-02-29", "10/11/2026", "20261110", "2026-11-1"]
    )
    def test_invalid(self, text: str) -> None:
        with pytest.raises(ValidationError, match="Invalid date"):
            services.parse_date(text)


class TestMonths:
    def test_parse_month(self) -> None:
        assert services.parse_month(" 2026-11 ") == "2026-11"

    @pytest.mark.parametrize("text", ["", "2026", "2026-13", "2026-00", "2026-1", "11-2026", "nov"])
    def test_parse_month_invalid(self, text: str) -> None:
        with pytest.raises(ValidationError, match="Invalid month"):
            services.parse_month(text)

    @pytest.mark.parametrize(
        ("month", "last_day"), [("2026-11", 30), ("2026-12", 31), ("2024-02", 29), ("2025-02", 28)]
    )
    def test_month_range(self, month: str, last_day: int) -> None:
        start, end = services.month_range(month)

        assert start.day == 1
        assert end.day == last_day
        assert start.isoformat()[:7] == end.isoformat()[:7] == month


class TestResolveDateRange:
    def test_nothing_given(self) -> None:
        assert services.resolve_date_range(None, None, None) == (None, None)

    def test_month(self) -> None:
        assert services.resolve_date_range(None, None, "2026-11") == (
            date(2026, 11, 1),
            date(2026, 11, 30),
        )

    def test_open_ended(self) -> None:
        assert services.resolve_date_range("2026-11-05", None, None) == (date(2026, 11, 5), None)
        assert services.resolve_date_range(None, "2026-11-05", None) == (None, date(2026, 11, 5))

    def test_same_day_is_allowed(self) -> None:
        day = date(2026, 11, 5)
        assert services.resolve_date_range("2026-11-05", "2026-11-05", None) == (day, day)

    @pytest.mark.parametrize(("start", "end"), [("2026-11-01", None), (None, "2026-11-30")])
    def test_month_with_explicit_range(self, start: str | None, end: str | None) -> None:
        with pytest.raises(ValidationError, match="not both"):
            services.resolve_date_range(start, end, "2026-11")

    def test_from_after_to(self) -> None:
        with pytest.raises(ValidationError, match="must not be after"):
            services.resolve_date_range("2026-11-10", "2026-11-01", None)


class TestCleanNote:
    def test_collapses_whitespace(self) -> None:
        assert services.clean_note("  lunch \n  plov ") == "lunch plov"

    def test_too_long(self) -> None:
        assert len(services.clean_note("x" * services.MAX_NOTE_LENGTH)) == services.MAX_NOTE_LENGTH
        with pytest.raises(ValidationError, match="too long"):
            services.clean_note("x" * (services.MAX_NOTE_LENGTH + 1))


class TestExpenseService:
    def test_add(self, service: ExpenseService) -> None:
        expense = service.add("45 000", "Food", "  lunch plov ", "2026-11-10")

        assert expense.amount == 45_000
        assert expense.category == "food"
        assert expense.note == "lunch plov"
        assert expense.spent_on == date(2026, 11, 10)

    def test_add_defaults_to_today_and_empty_note(self, service: ExpenseService) -> None:
        expense = service.add("100", "food")

        assert expense.spent_on == date.today()
        assert expense.note == ""

    def test_add_unknown_category_lists_available_ones(self, service: ExpenseService) -> None:
        with pytest.raises(NotFoundError) as excinfo:
            service.add("100", "pets")

        message = str(excinfo.value)
        assert "Unknown category 'pets'" in message
        assert "food" in message
        assert "spendr category add" in message

    def test_add_invalid_input_stores_nothing(self, service: ExpenseService) -> None:
        for args in [("-5", "food"), ("100", "pets"), ("100", "food", "", "2026-13-01")]:
            with pytest.raises((ValidationError, NotFoundError)):
                service.add(*args)

        assert service.find() == []

    def test_get_missing(self, service: ExpenseService) -> None:
        with pytest.raises(NotFoundError, match="No expense with id 5"):
            service.get(5)

    def test_find_empty_database(self, service: ExpenseService) -> None:
        assert service.find() == []
        assert service.find(category="food", month="2026-11", limit=5) == []

    def test_find_filters(self, service: ExpenseService) -> None:
        service.add("10", "food", "oct", "2026-10-31")
        service.add("20", "food", "nov", "2026-11-01")
        service.add("30", "transport", "bus", "2026-11-30")

        def notes(**filters: str | int | None) -> list[str]:
            return [e.note for e in service.find(**filters)]  # type: ignore[arg-type]

        assert notes(month="2026-11") == ["bus", "nov"]
        assert notes(category="FOOD") == ["nov", "oct"]
        assert notes(date_from="2026-11-01", date_to="2026-11-01") == ["nov"]
        assert notes(limit=1) == ["bus"]
        assert notes(category="food", month="2026-11") == ["nov"]

    @pytest.mark.parametrize("limit", [0, -3])
    def test_find_rejects_bad_limit(self, service: ExpenseService, limit: int) -> None:
        with pytest.raises(ValidationError, match="--limit"):
            service.find(limit=limit)

    def test_find_unknown_category(self, service: ExpenseService) -> None:
        with pytest.raises(NotFoundError, match="Unknown category"):
            service.find(category="pets")

    def test_edit(self, service: ExpenseService) -> None:
        original = service.add("100", "food", "tea", "2026-11-01")

        edited = service.edit(
            original.id, amount="250", category="transport", spent_on="2026-11-02"
        )

        assert (edited.amount, edited.category, edited.note) == (250, "transport", "tea")
        assert edited.spent_on == date(2026, 11, 2)

    def test_edit_can_clear_note(self, service: ExpenseService) -> None:
        original = service.add("100", "food", "tea")

        assert service.edit(original.id, note="").note == ""

    def test_edit_without_changes(self, service: ExpenseService) -> None:
        original = service.add("100", "food")

        with pytest.raises(ValidationError, match="Nothing to change"):
            service.edit(original.id)

    def test_edit_missing_expense(self, service: ExpenseService) -> None:
        with pytest.raises(NotFoundError, match="No expense with id 9"):
            service.edit(9, amount="not even valid")

    def test_edit_invalid_value_leaves_expense_untouched(self, service: ExpenseService) -> None:
        original = service.add("100", "food", "tea", "2026-11-01")

        with pytest.raises(ValidationError):
            service.edit(original.id, amount="200", spent_on="yesterday")

        assert service.get(original.id) == original

    def test_delete_returns_removed_expense(self, service: ExpenseService) -> None:
        original = service.add("100", "food")

        assert service.delete(original.id) == original
        assert service.find() == []

    def test_delete_missing_expense(self, service: ExpenseService) -> None:
        with pytest.raises(NotFoundError):
            service.delete(1)


class TestCleanCategoryName:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [("Food", "food"), ("  Pets  &   Vet ", "pets & vet"), ("eating-out_2", "eating-out_2")],
    )
    def test_valid(self, text: str, expected: str) -> None:
        assert services.clean_category_name(text) == expected

    def test_non_ascii_letters_are_allowed(self) -> None:
        assert services.clean_category_name("Озиқ-овқат") == "озиқ-овқат"

    @pytest.mark.parametrize("text", ["", "   "])
    def test_empty(self, text: str) -> None:
        with pytest.raises(ValidationError, match="cannot be empty"):
            services.clean_category_name(text)

    def test_too_long(self) -> None:
        with pytest.raises(ValidationError, match="too long"):
            services.clean_category_name("x" * (services.MAX_CATEGORY_LENGTH + 1))

    @pytest.mark.parametrize("text", ["a/b", "food!", "[red]", "a,b"])
    def test_invalid_characters(self, text: str) -> None:
        with pytest.raises(ValidationError, match="Invalid category name"):
            services.clean_category_name(text)


class TestCategoryService:
    def test_usage_starts_with_defaults(self, categories: CategoryService) -> None:
        names = [item.category.name for item in categories.usage()]

        assert names == sorted(db.DEFAULT_CATEGORIES)

    def test_add_normalizes_name(self, categories: CategoryService) -> None:
        assert categories.add("  Pets ").name == "pets"

    @pytest.mark.parametrize("name", ["food", "FOOD", " Food "])
    def test_add_duplicate(self, categories: CategoryService, name: str) -> None:
        with pytest.raises(DuplicateError, match="'food' already exists"):
            categories.add(name)

    def test_add_duplicate_non_ascii_name_ignoring_case(self, categories: CategoryService) -> None:
        categories.add("Еда")

        with pytest.raises(DuplicateError):
            categories.add("ЕДА")

    def test_rename_keeps_expenses(
        self, categories: CategoryService, service: ExpenseService
    ) -> None:
        expense = service.add("100", "food")

        renamed = categories.rename("Food", "Groceries")

        assert renamed.name == "groceries"
        assert service.get(expense.id).category == "groceries"

    def test_rename_unknown_category(self, categories: CategoryService) -> None:
        with pytest.raises(NotFoundError, match="Unknown category 'pets'"):
            categories.rename("pets", "animals")

    def test_rename_to_existing_name(self, categories: CategoryService) -> None:
        with pytest.raises(DuplicateError, match="'transport' already exists"):
            categories.rename("food", "transport")

    def test_rename_to_same_name(self, categories: CategoryService) -> None:
        with pytest.raises(ValidationError, match="already named 'food'"):
            categories.rename("food", "FOOD")

    def test_rename_to_invalid_name(self, categories: CategoryService) -> None:
        with pytest.raises(ValidationError, match="cannot be empty"):
            categories.rename("food", " ")

    def test_remove_unused(self, categories: CategoryService) -> None:
        assert categories.remove("Other").name == "other"
        assert "other" not in [item.category.name for item in categories.usage()]

    def test_remove_unknown(self, categories: CategoryService) -> None:
        with pytest.raises(NotFoundError):
            categories.remove("pets")

    @pytest.mark.parametrize(("count", "phrase"), [(1, "1 expense."), (2, "2 expenses.")])
    def test_remove_in_use(
        self, categories: CategoryService, service: ExpenseService, count: int, phrase: str
    ) -> None:
        for _ in range(count):
            service.add("100", "food")

        with pytest.raises(CategoryInUseError) as excinfo:
            categories.remove("food")

        assert f"'food' still has {phrase}" in str(excinfo.value)

    def test_all_categories_can_be_removed(
        self, categories: CategoryService, service: ExpenseService
    ) -> None:
        for name in db.DEFAULT_CATEGORIES:
            categories.remove(name)

        assert categories.usage() == []
        with pytest.raises(NotFoundError, match="Available: none yet"):
            service.add("100", "food")


class TestSummaryService:
    def test_empty_month(self, summaries: SummaryService) -> None:
        summary = summaries.for_month("2026-11")

        assert summary.month == "2026-11"
        assert summary.rows == []
        assert summary.total == 0
        assert summary.count == 0

    def test_defaults_to_current_month(
        self, summaries: SummaryService, service: ExpenseService
    ) -> None:
        service.add("100", "food")

        summary = summaries.for_month()

        assert summary.month == services.current_month()
        assert summary.total == 100

    def test_totals_and_percentages(
        self, summaries: SummaryService, service: ExpenseService
    ) -> None:
        service.add("250", "food", "", "2026-11-01")
        service.add("250", "food", "", "2026-11-30")
        service.add("1500", "housing", "", "2026-11-15")
        service.add("9999", "food", "", "2026-10-31")
        service.add("9999", "food", "", "2026-12-01")

        summary = summaries.for_month("2026-11")

        assert [(r.category, r.total, r.count, r.percent) for r in summary.rows] == [
            ("housing", 1500, 1, 75.0),
            ("food", 500, 2, 25.0),
        ]
        assert summary.total == 2000
        assert summary.count == 3

    def test_percentages_sum_to_one_hundred(
        self, summaries: SummaryService, service: ExpenseService
    ) -> None:
        for category in ("food", "transport", "health"):
            service.add("1", category, "", "2026-11-01")

        summary = summaries.for_month("2026-11")

        assert sum(row.percent for row in summary.rows) == pytest.approx(100)

    def test_invalid_month(self, summaries: SummaryService) -> None:
        with pytest.raises(ValidationError, match="Invalid month"):
            summaries.for_month("2026-13")


class TestBudgetService:
    def test_set_creates_then_edits(self, budgets: BudgetService) -> None:
        created, before = budgets.set("Food", "1 500 000", "2026-11")
        edited, previous = budgets.set("food", "1200000", "2026-11")

        assert (created.category, created.month, created.amount) == ("food", "2026-11", 1_500_000)
        assert before is None
        assert edited.amount == 1_200_000
        assert previous == 1_500_000

    def test_set_defaults_to_current_month(self, budgets: BudgetService) -> None:
        budget, _ = budgets.set("food", "100")

        assert budget.month == services.current_month()

    @pytest.mark.parametrize(
        ("args", "error", "message"),
        [
            (("pets", "100", "2026-11"), NotFoundError, "Unknown category"),
            (("food", "0", "2026-11"), ValidationError, "greater than zero"),
            (("food", "-100", "2026-11"), ValidationError, "greater than zero"),
            (("food", "1.5", "2026-11"), ValidationError, "Invalid amount"),
            (("food", "100", "2026-13"), ValidationError, "Invalid month"),
        ],
    )
    def test_set_invalid(
        self,
        budgets: BudgetService,
        args: tuple[str, str, str],
        error: type[Exception],
        message: str,
    ) -> None:
        with pytest.raises(error, match=message):
            budgets.set(*args)

        assert budgets.status("2026-11").is_empty

    def test_remove(self, budgets: BudgetService) -> None:
        budgets.set("food", "100", "2026-11")

        assert budgets.remove("food", "2026-11").amount == 100
        assert budgets.status("2026-11").is_empty

    def test_remove_missing(self, budgets: BudgetService) -> None:
        with pytest.raises(NotFoundError, match="No budget set for 'food' in 2026-11"):
            budgets.remove("food", "2026-11")
        with pytest.raises(NotFoundError, match="Unknown category"):
            budgets.remove("pets", "2026-11")

    def test_overall_budget_set_edit_remove(self, budgets: BudgetService) -> None:
        assert budgets.set_total("5000000", "2026-11") == ("2026-11", 5_000_000, None)
        assert budgets.set_total("4000000", "2026-11") == ("2026-11", 4_000_000, 5_000_000)
        assert budgets.status("2026-11").overall_budget == 4_000_000

        assert budgets.remove_total("2026-11") == ("2026-11", 4_000_000)
        assert budgets.status("2026-11").overall_budget is None

    def test_overall_budget_invalid(self, budgets: BudgetService) -> None:
        with pytest.raises(ValidationError, match="greater than zero"):
            budgets.set_total("0", "2026-11")
        with pytest.raises(ValidationError, match="Invalid month"):
            budgets.set_total("100", "nov")
        with pytest.raises(NotFoundError, match="No overall budget set for 2026-11"):
            budgets.remove_total("2026-11")

    def test_status_empty(self, budgets: BudgetService) -> None:
        report = budgets.status("2026-11", today=NOV_11)

        assert report.is_empty
        assert report.lines == []
        assert report.total_spent == 0

    def test_status_compares_spending_with_budgets(
        self, budgets: BudgetService, service: ExpenseService
    ) -> None:
        budgets.set("food", "1000", "2026-11")
        budgets.set("housing", "5000", "2026-11")
        budgets.set("health", "300", "2026-11")
        budgets.set("food", "1", "2026-12")
        service.add("950", "food", "", "2026-11-05")
        service.add("5001", "housing", "", "2026-11-01")
        service.add("70", "transport", "", "2026-11-03")
        service.add("999", "food", "", "2026-10-31")

        report = budgets.status("2026-11", today=NOV_11)

        assert [(line.category, line.budget, line.spent, line.state) for line in report.lines] == [
            ("food", 1000, 950, BudgetState.WARNING),
            ("health", 300, 0, BudgetState.OK),
            ("housing", 5000, 5001, BudgetState.OVER),
        ]
        assert [(item.category, item.total) for item in report.unbudgeted] == [("transport", 70)]
        assert report.total_spent == 6021
        assert report.overall_budget is None
        assert report.limit == 6300

    def test_overall_budget_is_independent_of_category_budgets(
        self, budgets: BudgetService, service: ExpenseService
    ) -> None:
        budgets.set("food", "1000", "2026-11")
        budgets.set_total("10000", "2026-11")
        service.add("400", "food", "", "2026-11-05")
        service.add("600", "transport", "", "2026-11-05")

        report = budgets.status("2026-11", today=NOV_11)

        assert report.limit == 10_000
        assert report.remaining == 9_000
        assert report.unallocated == 9_000
        assert report.unbudgeted_spent == 600

    def test_status_with_only_overall_budget(
        self, budgets: BudgetService, service: ExpenseService
    ) -> None:
        budgets.set_total("1000", "2026-11")
        service.add("400", "food", "", "2026-11-05")

        report = budgets.status("2026-11", today=NOV_11)

        assert not report.is_empty
        assert report.lines == []
        assert report.remaining == 600

    @pytest.mark.parametrize(
        ("today", "days_left", "is_past"),
        [
            (date(2026, 11, 1), 30, False),
            (NOV_11, 20, False),
            (date(2026, 11, 30), 1, False),
            (date(2026, 12, 1), None, True),
            (date(2026, 10, 31), None, False),
        ],
    )
    def test_status_days_left(
        self, budgets: BudgetService, today: date, days_left: int | None, is_past: bool
    ) -> None:
        report = budgets.status("2026-11", today=today)

        assert report.days_left == days_left
        assert report.is_past is is_past

    def test_status_defaults_to_month_of_today(self, budgets: BudgetService) -> None:
        assert budgets.status(today=date(2025, 2, 10)).month == "2025-02"
        assert budgets.status().month == services.current_month()

    def test_status_invalid_month(self, budgets: BudgetService) -> None:
        with pytest.raises(ValidationError, match="Invalid month"):
            budgets.status("2026-00")

    def test_renaming_category_keeps_budget(
        self, budgets: BudgetService, categories: CategoryService
    ) -> None:
        budgets.set("food", "1000", "2026-11")
        categories.rename("food", "groceries")

        assert [line.category for line in budgets.status("2026-11").lines] == ["groceries"]
