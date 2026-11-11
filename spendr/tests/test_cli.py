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

        for command in ("add", "list", "edit", "delete"):
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
