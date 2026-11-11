import json
from datetime import date
from pathlib import Path

import pytest
from typer.testing import CliRunner

from spendr import __version__, config
from spendr.cli import app

runner = CliRunner()


def run(*args: str, input: str | None = None, ok: bool = True) -> str:
    """Invoke the CLI, check the exit code and return everything it printed."""
    result = runner.invoke(app, list(args), input=input)
    assert (result.exit_code == 0) is ok, result.output
    # Expected failures must be reported as messages, never as tracebacks.
    assert result.exception is None or isinstance(result.exception, SystemExit)
    assert "Traceback" not in result.output
    return result.output


class TestApp:
    def test_version_flag_prints_version(self) -> None:
        assert run("--version").strip() == f"spendr {__version__}"

    def test_help_lists_commands(self) -> None:
        output = run("--help")

        for command in (
            "add",
            "list",
            "edit",
            "delete",
            "summary",
            "category",
            "budget",
            "config",
            "export",
            "import",
        ):
            assert command in output

    def test_no_arguments_shows_help(self) -> None:
        result = runner.invoke(app, [])

        assert "Usage" in result.output

    def test_database_is_created_at_spendr_db(self, cli_env: Path) -> None:
        run("list")

        assert (cli_env / "cli.db").is_file()

    def test_corrupt_database_is_reported(self, cli_env: Path) -> None:
        (cli_env / "cli.db").write_text("garbage " * 200)

        assert "not a usable spendr database" in run("list", ok=False)

    def test_broken_config_is_reported(self, cli_env: Path) -> None:
        (cli_env / "config.json").write_text("{oops")

        assert "not valid JSON" in run("list", ok=False)

    def test_currency_comes_from_config(self) -> None:
        config.save_config(config.Config(currency="USD"))

        assert "1 500 USD" in run("add", "1500", "food")


class TestAdd:
    def test_add_with_note_and_date(self) -> None:
        output = run("add", "45000", "food", "lunch plov", "--date", "2026-11-10")

        assert "Added #1 · 45 000 UZS · food · 2026-11-10 · lunch plov" in output

    def test_add_defaults_to_today(self) -> None:
        assert f"food · {date.today().isoformat()}" in run("add", "100", "food")

    @pytest.mark.parametrize(
        ("args", "message"),
        [
            (["-5", "food"], "greater than zero"),
            (["0", "food"], "greater than zero"),
            (["12.50", "food"], "Invalid amount '12.50'"),
            (["lots", "food"], "Invalid amount 'lots'"),
            (["100", "pets"], "Unknown category 'pets'"),
            (["100", "food", "--date", "2026-02-30"], "Invalid date '2026-02-30'"),
            (["100", "food", "--date", "yesterday"], "Invalid date 'yesterday'"),
            (["100", "food", "x" * 201], "Note is too long"),
        ],
    )
    def test_invalid_input(self, args: list[str], message: str) -> None:
        output = run("add", *args, ok=False)

        assert "Error:" in output
        assert message in output
        assert "No expenses found." in run("list")

    def test_missing_arguments(self) -> None:
        assert "Missing argument" in run("add", "100", ok=False)


class TestList:
    @pytest.fixture(autouse=True)
    def _seed(self) -> None:
        run("add", "10000", "food", "october", "-d", "2026-10-31")
        run("add", "45000", "food", "lunch plov", "-d", "2026-11-10")
        run("add", "1250000", "housing", "rent", "-d", "2026-11-01")
        run("add", "7000", "transport", "taxi", "-d", "2026-12-01")

    def test_lists_everything_newest_first(self) -> None:
        output = run("list")

        positions = [output.index(note) for note in ("taxi", "lunch plov", "rent", "october")]
        assert positions == sorted(positions)
        assert "4 expenses · total 1 312 000 UZS" in output

    def test_filter_by_month(self) -> None:
        output = run("list", "--month", "2026-11")

        assert "lunch plov" in output
        assert "rent" in output
        assert "october" not in output
        assert "taxi" not in output
        assert "total 1 295 000 UZS" in output

    def test_filter_by_category(self) -> None:
        output = run("list", "--category", "food")

        assert "2 expenses" in output
        assert "rent" not in output

    def test_filter_by_date_range(self) -> None:
        output = run("list", "--from", "2026-11-01", "--to", "2026-11-10")

        assert "2 expenses" in output

    def test_limit(self) -> None:
        output = run("list", "--limit", "1")

        assert "taxi" in output
        assert "1 expense ·" in output

    def test_no_matches(self) -> None:
        assert "No expenses found." in run("list", "--from", "2030-01-01")

    @pytest.mark.parametrize(
        ("args", "message"),
        [
            (["--month", "2026-13"], "Invalid month '2026-13'"),
            (["--from", "nope"], "Invalid date 'nope'"),
            (["--from", "2026-11-10", "--to", "2026-11-01"], "must not be after"),
            (["--month", "2026-11", "--from", "2026-11-01"], "not both"),
            (["--category", "pets"], "Unknown category 'pets'"),
            (["--limit", "0"], "--limit must be at least 1"),
        ],
    )
    def test_invalid_filters(self, args: list[str], message: str) -> None:
        assert message in run("list", *args, ok=False)

    def test_non_numeric_limit(self) -> None:
        assert "Invalid value" in run("list", "--limit", "many", ok=False)


def test_list_on_empty_database() -> None:
    assert "No expenses found." in run("list")


class TestEdit:
    @pytest.fixture(autouse=True)
    def _seed(self) -> None:
        run("add", "45000", "food", "lunch plov", "-d", "2026-11-10")

    def test_edit_several_fields(self) -> None:
        output = run(
            "edit", "1", "--amount", "50000", "--category", "other", "--date", "2026-11-09"
        )

        assert "Updated #1 · 50 000 UZS · other · 2026-11-09 · lunch plov" in output

    def test_edit_clears_note(self) -> None:
        output = run("edit", "1", "--note", "")

        assert output.strip().endswith("2026-11-10")

    @pytest.mark.parametrize(
        ("args", "message"),
        [
            (["1"], "Nothing to change"),
            (["2", "--amount", "5"], "No expense with id 2"),
            (["1", "--amount", "-5"], "greater than zero"),
            (["1", "--category", "pets"], "Unknown category"),
            (["1", "--date", "10.11.2026"], "Invalid date"),
        ],
    )
    def test_invalid_edits(self, args: list[str], message: str) -> None:
        assert message in run("edit", *args, ok=False)
        assert "45 000" in run("list")

    def test_non_numeric_id(self) -> None:
        assert "Invalid value" in run("edit", "first", "--amount", "5", ok=False)


class TestDelete:
    @pytest.fixture(autouse=True)
    def _seed(self) -> None:
        run("add", "45000", "food", "lunch plov", "-d", "2026-11-10")

    def test_confirmed(self) -> None:
        output = run("delete", "1", input="y\n")

        assert "Delete #1 · 45 000 UZS · food · 2026-11-10 · lunch plov?" in output
        assert "Deleted #1" in output
        assert "No expenses found." in run("list")

    @pytest.mark.parametrize("answer", ["n\n", "\n"])
    def test_declined_keeps_expense(self, answer: str) -> None:
        output = run("delete", "1", input=answer)

        assert "Cancelled." in output
        assert "lunch plov" in run("list")

    def test_yes_flag_skips_confirmation(self) -> None:
        output = run("delete", "1", "--yes")

        assert "?" not in output
        assert "Deleted #1" in output

    def test_missing_expense_fails_before_asking(self) -> None:
        output = run("delete", "42", ok=False)

        assert "No expense with id 42" in output
        assert "?" not in output


class TestSummary:
    def test_month_summary_with_chart(self) -> None:
        run("add", "1250000", "housing", "rent", "-d", "2026-11-01")
        run("add", "45000", "food", "lunch plov", "-d", "2026-11-10")
        run("add", "120000", "food", "market", "-d", "2026-11-05")
        run("add", "999", "food", "other month", "-d", "2026-12-01")

        output = run("summary", "--month", "2026-11")

        assert "Summary for 2026-11" in output
        assert "1 250 000" in output
        assert "165 000" in output
        assert "1 415 000" in output
        assert "88.3%" in output
        assert "11.7%" in output
        assert "█" in output
        assert output.index("housing") < output.index("food")

    def test_defaults_to_current_month(self) -> None:
        run("add", "100", "food")

        assert f"Summary for {date.today():%Y-%m}" in run("summary")

    def test_empty_month(self) -> None:
        assert "No expenses in 2026-11." in run("summary", "-m", "2026-11")

    def test_invalid_month(self) -> None:
        assert "Invalid month 'november'" in run("summary", "-m", "november", ok=False)


class TestCategory:
    def test_list_shows_defaults_with_counts(self) -> None:
        run("add", "100", "food")

        output = run("category", "list")

        assert "transport" in output
        food_line = next(line for line in output.splitlines() if "food" in line)
        assert "1" in food_line

    def test_add_then_use(self) -> None:
        assert "Added category 'pets'" in run("category", "add", "Pets")
        assert "pets" in run("add", "100", "pets")

    @pytest.mark.parametrize(
        ("name", "message"),
        [("food", "already exists"), ("  ", "cannot be empty"), ("a/b", "Invalid category name")],
    )
    def test_add_invalid(self, name: str, message: str) -> None:
        assert message in run("category", "add", name, ok=False)

    def test_rename(self) -> None:
        run("add", "100", "food", "tea")

        assert "Renamed category to 'groceries'" in run("category", "rename", "food", "groceries")
        assert "groceries" in run("list")

    @pytest.mark.parametrize(
        ("args", "message"),
        [
            (["pets", "animals"], "Unknown category 'pets'"),
            (["food", "transport"], "already exists"),
            (["food", "Food"], "already named"),
        ],
    )
    def test_rename_invalid(self, args: list[str], message: str) -> None:
        assert message in run("category", "rename", *args, ok=False)

    def test_remove(self) -> None:
        assert "Removed category 'other'" in run("category", "remove", "other")
        assert "other" not in run("category", "list")

    def test_remove_in_use_is_refused(self) -> None:
        run("add", "100", "food")

        assert "still has 1 expense" in run("category", "remove", "food", ok=False)
        assert "food" in run("category", "list")

    def test_remove_unknown(self) -> None:
        assert "Unknown category" in run("category", "remove", "pets", ok=False)

    def test_list_when_all_removed(self) -> None:
        for line in run("category", "list").splitlines():
            cells = [cell.strip() for cell in line.split("│") if cell.strip()]
            if len(cells) == 2 and cells[1] == "0":
                run("category", "remove", cells[0])

        assert "No categories yet" in run("category", "list")


class TestConfig:
    def test_show_defaults(self, cli_env: Path) -> None:
        output = run("config", "show")

        assert "UZS" in output
        assert str(cli_env / "config.json") in output
        assert str(cli_env / "cli.db") in output

    def test_set_currency(self) -> None:
        assert "Currency set to USD" in run("config", "currency", "usd")
        assert "USD" in run("config", "show")
        assert "100 USD" in run("add", "100", "food")

    def test_invalid_currency(self) -> None:
        assert "Invalid currency" in run("config", "currency", "US D", ok=False)
        assert "UZS" in run("config", "show")

    def test_show_with_broken_config(self, cli_env: Path) -> None:
        (cli_env / "config.json").write_text("[]")

        assert "must contain a JSON object" in run("config", "show", ok=False)


class TestBudget:
    def test_set_then_edit(self) -> None:
        first = run("budget", "set", "food", "1500000", "--month", "2026-11")
        second = run("budget", "set", "food", "1200000", "--month", "2026-11")
        third = run("budget", "set", "food", "1200000", "--month", "2026-11")

        assert "Set food budget for 2026-11 to 1 500 000 UZS" in first
        assert "Changed food budget for 2026-11 from 1 500 000 UZS to 1 200 000 UZS" in second
        assert "Food budget for 2026-11 is already 1 200 000 UZS" in third

    def test_set_defaults_to_current_month(self) -> None:
        assert f"food budget for {date.today():%Y-%m}" in run("budget", "set", "food", "100")

    @pytest.mark.parametrize(
        ("args", "message"),
        [
            (["pets", "100"], "Unknown category 'pets'"),
            (["food", "-100"], "greater than zero"),
            (["food", "0"], "greater than zero"),
            (["food", "lots"], "Invalid amount"),
            (["food", "100", "--month", "2026-13"], "Invalid month"),
        ],
    )
    def test_set_invalid(self, args: list[str], message: str) -> None:
        assert message in run("budget", "set", *args, ok=False)

    def test_overall_budget_set_then_edit(self) -> None:
        first = run("budget", "total", "5000000", "-m", "2026-11")
        second = run("budget", "total", "4000000", "-m", "2026-11")

        assert "Set overall budget for 2026-11 to 5 000 000 UZS" in first
        assert "Changed overall budget for 2026-11 from 5 000 000 UZS to 4 000 000 UZS" in second

    def test_overall_budget_invalid(self) -> None:
        assert "greater than zero" in run("budget", "total", "-1", ok=False)

    def test_remove_category_budget(self) -> None:
        run("budget", "set", "food", "100", "-m", "2026-11")

        output = run("budget", "remove", "food", "-m", "2026-11")

        assert "Removed food budget for 2026-11 (100 UZS)" in output
        assert "No budgets set for 2026-11" in run("budget", "status", "-m", "2026-11")

    def test_remove_overall_budget(self) -> None:
        run("budget", "total", "100", "-m", "2026-11")

        assert "Removed overall budget for 2026-11 (100 UZS)" in run(
            "budget", "remove", "--total", "-m", "2026-11"
        )

    @pytest.mark.parametrize(
        ("args", "message"),
        [
            ([], "Give either a category or --total"),
            (["food", "--total"], "Give either a category or --total"),
            (["food", "-m", "2026-11"], "No budget set for 'food' in 2026-11"),
            (["--total", "-m", "2026-11"], "No overall budget set for 2026-11"),
            (["pets"], "Unknown category"),
        ],
    )
    def test_remove_invalid(self, args: list[str], message: str) -> None:
        assert message in run("budget", "remove", *args, ok=False)

    def test_status_without_budgets(self) -> None:
        output = run("budget", "status", "--month", "2026-11")

        assert "No budgets set for 2026-11" in output
        assert "spendr budget set CATEGORY AMOUNT" in output

    def test_status_shows_table_and_highlights(self) -> None:
        run("budget", "set", "food", "175000", "-m", "2026-10")
        run("budget", "set", "housing", "1200000", "-m", "2026-10")
        run("budget", "total", "2000000", "-m", "2026-10")
        run("add", "165000", "food", "-d", "2026-10-05")
        run("add", "1250000", "housing", "-d", "2026-10-01")
        run("add", "7000", "transport", "-d", "2026-10-03")

        output = run("budget", "status", "--month", "2026-10")

        assert "Budgets for 2026-10 (UZS)" in output
        food = next(line for line in output.splitlines() if "food" in line and "│" in line)
        assert "94%" in food and "near limit" in food
        assert "over budget" in output
        assert "Highlights" in output
        assert "Saved" in output and "578 000 UZS" in output
        assert "625 000 UZS not assigned to any category" in output
        assert "7 000 UZS spent on transport" in output

    def test_status_with_only_overall_budget(self) -> None:
        run("budget", "total", "1000", "-m", "2026-10")
        run("add", "1200", "food", "-d", "2026-10-05")

        output = run("budget", "status", "-m", "2026-10")

        assert "Budgets for" not in output
        assert "Over budget by" in output and "200 UZS" in output

    def test_status_defaults_to_current_month(self) -> None:
        run("budget", "total", "1000")
        run("add", "100", "food")

        output = run("budget", "status")

        assert "Left to spend" in output and "900 UZS" in output
        assert "Daily allowance" in output

    def test_status_invalid_month(self) -> None:
        assert "Invalid month" in run("budget", "status", "-m", "soon", ok=False)


class TestExport:
    @pytest.fixture(autouse=True)
    def _seed(self, cli_env: Path) -> None:
        run("add", "45000", "food", "lunch plov", "-d", "2026-11-10")
        run("add", "1250000", "housing", "rent", "-d", "2026-12-01")

    def test_csv_to_stdout_by_default(self) -> None:
        assert run("export").splitlines() == [
            "id,date,category,amount,note",
            "1,2026-11-10,food,45000,lunch plov",
            "2,2026-12-01,housing,1250000,rent",
        ]

    def test_json_to_stdout(self) -> None:
        records = json.loads(run("export", "--format", "json"))

        assert [record["amount"] for record in records] == [45_000, 1_250_000]

    def test_csv_to_file(self, cli_env: Path) -> None:
        path = cli_env / "out.csv"

        output = run("export", "--format", "csv", "--output", str(path))

        assert "Exported 2 expenses to" in output
        assert path.read_text().count("\n") == 3

    def test_json_to_file_with_filter(self, cli_env: Path) -> None:
        path = cli_env / "out.json"

        output = run("export", "-f", "json", "-o", str(path), "--month", "2026-11")

        assert "Exported 1 expense to" in output
        assert [record["note"] for record in json.loads(path.read_text())] == ["lunch plov"]

    def test_existing_file_needs_force(self, cli_env: Path) -> None:
        path = cli_env / "out.csv"
        path.write_text("precious")

        assert "already exists. Use --force" in run("export", "-o", str(path), ok=False)
        assert path.read_text() == "precious"

        run("export", "-o", str(path), "--force")
        assert path.read_text().startswith("id,date")

    @pytest.mark.parametrize(
        ("args", "message"),
        [
            (["--format", "xml"], "Invalid value"),
            (["--month", "2026-13"], "Invalid month"),
            (["--category", "pets"], "Unknown category"),
            (["--from", "2026-12-01", "--to", "2026-11-01"], "must not be after"),
        ],
    )
    def test_invalid_options(self, args: list[str], message: str) -> None:
        assert message in run("export", *args, ok=False)


def test_export_empty_database() -> None:
    assert run("export") == "id,date,category,amount,note\n"
    assert run("export", "-f", "json") == "[]\n"


class TestImport:
    def write(self, folder: Path, content: str) -> str:
        path = folder / "in.csv"
        path.write_text(content, encoding="utf-8")
        return str(path)

    def test_import(self, cli_env: Path) -> None:
        path = self.write(cli_env, "date,category,amount,note\n2026-11-10,food,45000,lunch plov\n")

        assert "Imported 1 expense" in run("import", path)
        assert "lunch plov" in run("list")

    def test_export_then_import_into_fresh_database(
        self, cli_env: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        run("add", "45000", "food", "lunch plov", "-d", "2026-11-10")
        run("add", "7000", "transport", "taxi", "-d", "2026-11-03")
        exported = cli_env / "backup.csv"
        run("export", "-o", str(exported))

        monkeypatch.setenv("SPENDR_DB", str(cli_env / "fresh.db"))
        output = run("import", str(exported))

        assert "Imported 2 expenses" in output
        assert "total 52 000 UZS" in run("list")

    def test_invalid_rows(self, cli_env: Path) -> None:
        path = self.write(cli_env, "date,category,amount\n2026-02-30,food,1\n2026-11-10,food,-1\n")

        output = run("import", path, ok=False)

        assert "2 invalid rows" in output
        assert "line 2: Invalid date '2026-02-30'" in output
        assert "line 3: Amount must be greater than zero" in output
        assert "No expenses found." in run("list")

    def test_unknown_category_then_create(self, cli_env: Path) -> None:
        path = self.write(cli_env, "date,category,amount\n2026-11-10,pets,100\n")

        assert "Unknown category in" in run("import", path, ok=False)

        dry = run("import", path, "--create-categories", "--dry-run")
        assert "Dry run: 1 expense would be imported (would create categories: pets)" in dry
        assert "No expenses found." in run("list")

        assert "Imported 1 expense (created categories: pets)" in run(
            "import", path, "--create-categories"
        )

    def test_skip_duplicates(self, cli_env: Path) -> None:
        path = self.write(cli_env, "date,category,amount\n2026-11-10,food,100\n2026-11-11,food,5\n")
        run("import", path)

        output = run("import", path, "--skip-duplicates")

        assert "Imported 0 expenses (2 duplicates skipped)" in output
        assert "2 expenses" in run("list")

    @pytest.mark.parametrize(
        ("content", "message"),
        [
            ("", "The file is empty"),
            ("a,b\n1,2\n", "Missing columns: date, category, amount"),
        ],
    )
    def test_unusable_file(self, cli_env: Path, content: str, message: str) -> None:
        assert message in run("import", self.write(cli_env, content), ok=False)

    def test_missing_file(self, cli_env: Path) -> None:
        assert "File not found" in run("import", str(cli_env / "nope.csv"), ok=False)

    def test_missing_argument(self) -> None:
        assert "Missing argument" in run("import", ok=False)
