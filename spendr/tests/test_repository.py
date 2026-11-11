from datetime import UTC, date, datetime

import pytest

from spendr.errors import CategoryInUseError, DuplicateError, NotFoundError
from spendr.models import ExpenseFilter
from spendr.repository import BudgetRepository, CategoryRepository, ExpenseRepository


def category_id(categories: CategoryRepository, name: str) -> int:
    category = categories.get_by_name(name)
    assert category is not None
    return category.id


class TestCategories:
    def test_add_and_get(self, categories: CategoryRepository) -> None:
        created = categories.add("gifts")

        assert categories.get(created.id) == created
        assert categories.get_by_name("gifts") == created

    def test_lookup_by_name_ignores_case(self, categories: CategoryRepository) -> None:
        food = categories.get_by_name("FOOD")

        assert food is not None
        assert food.name == "food"

    def test_get_missing_returns_none(self, categories: CategoryRepository) -> None:
        assert categories.get(9999) is None
        assert categories.get_by_name("nope") is None

    def test_list_is_sorted_by_name(self, categories: CategoryRepository) -> None:
        names = [category.name for category in categories.list_all()]

        assert names == sorted(names)
        assert "food" in names

    @pytest.mark.parametrize("name", ["food", "Food"])
    def test_add_duplicate_is_rejected(self, categories: CategoryRepository, name: str) -> None:
        with pytest.raises(DuplicateError, match="already exists"):
            categories.add(name)

    def test_rename(self, categories: CategoryRepository) -> None:
        food_id = category_id(categories, "food")

        renamed = categories.rename(food_id, "groceries")

        assert renamed.name == "groceries"
        assert categories.get_by_name("food") is None
        assert categories.get(food_id) == renamed

    def test_rename_to_existing_name_is_rejected(self, categories: CategoryRepository) -> None:
        with pytest.raises(DuplicateError):
            categories.rename(category_id(categories, "food"), "transport")

    def test_rename_missing_category(self, categories: CategoryRepository) -> None:
        with pytest.raises(NotFoundError):
            categories.rename(9999, "whatever")

    def test_remove_unused_category(self, categories: CategoryRepository) -> None:
        categories.remove(category_id(categories, "other"))

        assert categories.get_by_name("other") is None

    def test_remove_missing_category(self, categories: CategoryRepository) -> None:
        with pytest.raises(NotFoundError):
            categories.remove(9999)

    def test_remove_category_with_expenses_is_refused(
        self, categories: CategoryRepository, expenses: ExpenseRepository
    ) -> None:
        food_id = category_id(categories, "food")
        expenses.add(100, food_id, "", date(2026, 11, 1))
        expenses.add(200, food_id, "", date(2026, 11, 2))

        with pytest.raises(CategoryInUseError, match="2 expense"):
            categories.remove(food_id)

        assert categories.get(food_id) is not None

    def test_remove_category_also_removes_its_budgets(
        self, categories: CategoryRepository, budgets: BudgetRepository
    ) -> None:
        food_id = category_id(categories, "food")
        budgets.set(food_id, "2026-11", 1_000)

        categories.remove(food_id)

        assert budgets.list_for_month("2026-11") == []


class TestExpenses:
    def test_add_returns_stored_expense(
        self, categories: CategoryRepository, expenses: ExpenseRepository
    ) -> None:
        food_id = category_id(categories, "food")
        before = datetime.now(UTC).replace(microsecond=0)

        expense = expenses.add(45_000, food_id, "lunch plov", date(2026, 11, 10))

        assert expense.amount == 45_000
        assert expense.category_id == food_id
        assert expense.category == "food"
        assert expense.note == "lunch plov"
        assert expense.spent_on == date(2026, 11, 10)
        assert expense.created_at >= before
        assert expenses.get(expense.id) == expense

    def test_amount_round_trips_as_int(
        self, categories: CategoryRepository, expenses: ExpenseRepository
    ) -> None:
        huge = 9_007_199_254_740_993  # not representable as a float

        expense = expenses.add(huge, category_id(categories, "food"), "", date(2026, 1, 1))

        assert expense.amount == huge
        assert isinstance(expense.amount, int)

    def test_get_missing_returns_none(self, expenses: ExpenseRepository) -> None:
        assert expenses.get(1) is None

    def test_list_empty_database(self, expenses: ExpenseRepository) -> None:
        assert expenses.find() == []

    def test_list_orders_newest_first(
        self, categories: CategoryRepository, expenses: ExpenseRepository
    ) -> None:
        food_id = category_id(categories, "food")
        old = expenses.add(1, food_id, "", date(2026, 10, 1))
        same_day_first = expenses.add(2, food_id, "", date(2026, 11, 5))
        same_day_second = expenses.add(3, food_id, "", date(2026, 11, 5))

        ids = [expense.id for expense in expenses.find()]

        assert ids == [same_day_second.id, same_day_first.id, old.id]

    def test_list_filters(
        self, categories: CategoryRepository, expenses: ExpenseRepository
    ) -> None:
        food_id = category_id(categories, "food")
        transport_id = category_id(categories, "transport")
        expenses.add(10, food_id, "oct", date(2026, 10, 31))
        expenses.add(20, food_id, "nov start", date(2026, 11, 1))
        expenses.add(30, transport_id, "nov mid", date(2026, 11, 15))
        expenses.add(40, food_id, "nov end", date(2026, 11, 30))
        expenses.add(50, food_id, "dec", date(2026, 12, 1))

        def notes(filters: ExpenseFilter) -> list[str]:
            return [expense.note for expense in expenses.find(filters)]

        november = ExpenseFilter(date_from=date(2026, 11, 1), date_to=date(2026, 11, 30))
        assert notes(november) == ["nov end", "nov mid", "nov start"]
        assert notes(ExpenseFilter(category_id=transport_id)) == ["nov mid"]
        assert notes(ExpenseFilter(date_from=date(2026, 11, 30))) == ["dec", "nov end"]
        assert notes(ExpenseFilter(date_to=date(2026, 10, 31))) == ["oct"]
        assert notes(ExpenseFilter(limit=2)) == ["dec", "nov end"]
        assert notes(ExpenseFilter(category_id=food_id, date_from=date(2026, 11, 1), limit=1)) == [
            "dec"
        ]
        assert notes(ExpenseFilter(date_from=date(2027, 1, 1))) == []

    def test_update_changes_only_given_fields(
        self, categories: CategoryRepository, expenses: ExpenseRepository
    ) -> None:
        original = expenses.add(100, category_id(categories, "food"), "tea", date(2026, 11, 1))

        updated = expenses.update(original.id, amount=250, note="")

        assert updated.amount == 250
        assert updated.note == ""
        assert updated.category == "food"
        assert updated.spent_on == original.spent_on
        assert updated.created_at == original.created_at

    def test_update_category_and_date(
        self, categories: CategoryRepository, expenses: ExpenseRepository
    ) -> None:
        original = expenses.add(100, category_id(categories, "food"), "", date(2026, 11, 1))

        updated = expenses.update(
            original.id, category_id=category_id(categories, "transport"), spent_on=date(2026, 1, 2)
        )

        assert updated.category == "transport"
        assert updated.spent_on == date(2026, 1, 2)

    def test_update_without_changes_returns_expense_unchanged(
        self, categories: CategoryRepository, expenses: ExpenseRepository
    ) -> None:
        original = expenses.add(100, category_id(categories, "food"), "", date(2026, 11, 1))

        assert expenses.update(original.id) == original

    def test_update_missing_expense(self, expenses: ExpenseRepository) -> None:
        with pytest.raises(NotFoundError, match="No expense with id 42"):
            expenses.update(42, amount=1)

    def test_delete(self, categories: CategoryRepository, expenses: ExpenseRepository) -> None:
        expense = expenses.add(100, category_id(categories, "food"), "", date(2026, 11, 1))

        expenses.delete(expense.id)

        assert expenses.get(expense.id) is None

    def test_delete_missing_expense(self, expenses: ExpenseRepository) -> None:
        with pytest.raises(NotFoundError, match="No expense with id 7"):
            expenses.delete(7)

    def test_totals_by_category(
        self, categories: CategoryRepository, expenses: ExpenseRepository
    ) -> None:
        food_id = category_id(categories, "food")
        transport_id = category_id(categories, "transport")
        expenses.add(100, food_id, "", date(2026, 11, 1))
        expenses.add(300, transport_id, "", date(2026, 11, 2))
        expenses.add(50, food_id, "", date(2026, 11, 30))
        expenses.add(999, food_id, "", date(2026, 12, 1))

        totals = expenses.totals_by_category(date(2026, 11, 1), date(2026, 11, 30))

        assert [(t.category, t.total, t.count) for t in totals] == [
            ("transport", 300, 1),
            ("food", 150, 2),
        ]

    def test_totals_without_range_cover_everything(
        self, categories: CategoryRepository, expenses: ExpenseRepository
    ) -> None:
        food_id = category_id(categories, "food")
        expenses.add(100, food_id, "", date(2020, 1, 1))
        expenses.add(200, food_id, "", date(2030, 1, 1))

        totals = expenses.totals_by_category()

        assert [(t.category, t.total) for t in totals] == [("food", 300)]

    def test_totals_empty_database(self, expenses: ExpenseRepository) -> None:
        assert expenses.totals_by_category() == []


class TestBudgets:
    def test_set_creates_budget(
        self, categories: CategoryRepository, budgets: BudgetRepository
    ) -> None:
        food_id = category_id(categories, "food")

        budget = budgets.set(food_id, "2026-11", 1_500_000)

        assert budget.category == "food"
        assert budget.month == "2026-11"
        assert budget.amount == 1_500_000
        assert budgets.get(food_id, "2026-11") == budget

    def test_set_again_replaces_amount(
        self, categories: CategoryRepository, budgets: BudgetRepository
    ) -> None:
        food_id = category_id(categories, "food")
        first = budgets.set(food_id, "2026-11", 100)

        second = budgets.set(food_id, "2026-11", 200)

        assert second.id == first.id
        assert second.amount == 200
        assert len(budgets.list_for_month("2026-11")) == 1

    def test_budgets_are_per_month(
        self, categories: CategoryRepository, budgets: BudgetRepository
    ) -> None:
        food_id = category_id(categories, "food")
        budgets.set(food_id, "2026-11", 100)
        budgets.set(food_id, "2026-12", 200)
        budgets.set(category_id(categories, "transport"), "2026-11", 300)

        november = budgets.list_for_month("2026-11")

        assert [(b.category, b.amount) for b in november] == [("food", 100), ("transport", 300)]
        assert budgets.get(food_id, "2027-01") is None

    def test_list_for_month_without_budgets(self, budgets: BudgetRepository) -> None:
        assert budgets.list_for_month("2026-11") == []

    def test_remove(self, categories: CategoryRepository, budgets: BudgetRepository) -> None:
        food_id = category_id(categories, "food")
        budgets.set(food_id, "2026-11", 100)

        budgets.remove(food_id, "2026-11")

        assert budgets.get(food_id, "2026-11") is None

    def test_remove_missing_budget(
        self, categories: CategoryRepository, budgets: BudgetRepository
    ) -> None:
        with pytest.raises(NotFoundError, match="No budget"):
            budgets.remove(category_id(categories, "food"), "2026-11")
