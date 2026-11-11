import sqlite3
from datetime import date

import pytest

from spendr import services
from spendr.errors import NotFoundError, ValidationError
from spendr.services import ExpenseService


@pytest.fixture
def service(conn: sqlite3.Connection) -> ExpenseService:
    return ExpenseService(conn)


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
        with pytest.raises(NotFoundError, match=r"Unknown category 'pets'\. Available: .*food"):
            service.add("100", "pets")

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
