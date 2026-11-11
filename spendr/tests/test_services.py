import sqlite3
from datetime import date

import pytest

from spendr import db, services
from spendr.errors import CategoryInUseError, DuplicateError, NotFoundError, ValidationError
from spendr.services import CategoryService, ExpenseService, SummaryService


@pytest.fixture
def service(conn: sqlite3.Connection) -> ExpenseService:
    return ExpenseService(conn)


@pytest.fixture
def categories(conn: sqlite3.Connection) -> CategoryService:
    return CategoryService(conn)


@pytest.fixture
def summaries(conn: sqlite3.Connection) -> SummaryService:
    return SummaryService(conn)


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
