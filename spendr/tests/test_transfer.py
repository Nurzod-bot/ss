import csv
import io
import json
import sqlite3
from pathlib import Path

import pytest

from spendr import db
from spendr.errors import NotFoundError, ValidationError
from spendr.services import ExpenseService
from spendr.transfer import (
    ExportFormat,
    TransferService,
    parse_csv,
    read_text,
    write_text,
)


@pytest.fixture
def expenses(conn: sqlite3.Connection) -> ExpenseService:
    return ExpenseService(conn)


@pytest.fixture
def transfer(conn: sqlite3.Connection) -> TransferService:
    return TransferService(conn)


@pytest.fixture
def seeded(expenses: ExpenseService) -> ExpenseService:
    expenses.add("45000", "food", "lunch plov", "2026-11-10")
    expenses.add("1250000", "housing", 'rent, "paid" in cash', "2026-11-01")
    expenses.add("7000", "transport", "", "2026-12-03")
    return expenses


def csv_file(tmp_path: Path, content: str, name: str = "in.csv") -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


class TestExport:
    @pytest.mark.usefixtures("seeded")
    def test_csv(self, transfer: TransferService) -> None:
        text, count = transfer.export(ExportFormat.CSV)

        rows = list(csv.DictReader(io.StringIO(text)))
        assert count == 3
        assert text.splitlines()[0] == "id,date,category,amount,note"
        assert [row["date"] for row in rows] == ["2026-11-01", "2026-11-10", "2026-12-03"]
        assert rows[0] == {
            "id": "2",
            "date": "2026-11-01",
            "category": "housing",
            "amount": "1250000",
            "note": 'rent, "paid" in cash',
        }

    @pytest.mark.usefixtures("seeded")
    def test_json(self, transfer: TransferService) -> None:
        text, count = transfer.export(ExportFormat.JSON)

        records = json.loads(text)
        assert count == 3
        assert records[1] == {
            "id": 1,
            "date": "2026-11-10",
            "category": "food",
            "amount": 45000,
            "note": "lunch plov",
        }
        assert isinstance(records[1]["amount"], int)

    def test_json_keeps_non_ascii_text_readable(
        self, transfer: TransferService, expenses: ExpenseService
    ) -> None:
        expenses.add("100", "food", "чой ☕", "2026-11-10")

        assert "чой ☕" in transfer.export(ExportFormat.JSON)[0]

    @pytest.mark.usefixtures("seeded")
    def test_filters(self, transfer: TransferService) -> None:
        assert transfer.export(ExportFormat.CSV, month="2026-11")[1] == 2
        assert transfer.export(ExportFormat.CSV, category="food")[1] == 1
        assert (
            transfer.export(ExportFormat.CSV, date_from="2026-11-10", date_to="2026-12-31")[1] == 2
        )

    def test_invalid_filters(self, transfer: TransferService) -> None:
        with pytest.raises(ValidationError, match="Invalid month"):
            transfer.export(ExportFormat.CSV, month="2026-13")
        with pytest.raises(NotFoundError, match="Unknown category"):
            transfer.export(ExportFormat.CSV, category="pets")

    def test_empty_database(self, transfer: TransferService) -> None:
        assert transfer.export(ExportFormat.CSV) == ("id,date,category,amount,note\n", 0)
        assert transfer.export(ExportFormat.JSON) == ("[]\n", 0)


class TestFiles:
    def test_write_then_read(self, tmp_path: Path) -> None:
        path = tmp_path / "out.csv"

        write_text(path, "a,b\n1,2\n")

        assert path.read_bytes() == b"a,b\n1,2\n"
        assert read_text(path) == "a,b\n1,2\n"

    def test_existing_file_is_kept_unless_forced(self, tmp_path: Path) -> None:
        path = tmp_path / "out.csv"
        path.write_text("precious")

        with pytest.raises(ValidationError, match="already exists"):
            write_text(path, "new")
        assert path.read_text() == "precious"

        write_text(path, "new", overwrite=True)
        assert path.read_text() == "new"

    def test_unwritable_path(self, tmp_path: Path) -> None:
        with pytest.raises(ValidationError, match="Cannot write"):
            write_text(tmp_path / "missing-folder" / "out.csv", "x")

    def test_read_strips_excel_byte_order_mark(self, tmp_path: Path) -> None:
        path = tmp_path / "excel.csv"
        path.write_bytes(b"\xef\xbb\xbfdate,category,amount\n")

        assert read_text(path).startswith("date")

    def test_read_errors(self, tmp_path: Path) -> None:
        with pytest.raises(ValidationError, match="File not found"):
            read_text(tmp_path / "nope.csv")
        with pytest.raises(ValidationError, match="Cannot read"):
            read_text(tmp_path)
        binary = tmp_path / "photo.csv"
        binary.write_bytes(b"\xff\xfe\x00\x01\x80")
        with pytest.raises(ValidationError, match="not a UTF-8 text file"):
            read_text(binary)


class TestParseCsv:
    def test_valid_rows(self) -> None:
        rows, errors = parse_csv(
            "id,date,category,amount,note,extra\n"
            "7,2026-11-10,Food,45 000,lunch plov,ignored\n"
            "\n"
            '8,2026-11-01,housing,1250000,"rent, in cash"\n'
        )

        assert errors == []
        assert [(r.line, r.spent_on.isoformat(), r.category, r.amount, r.note) for r in rows] == [
            (2, "2026-11-10", "food", 45_000, "lunch plov"),
            (4, "2026-11-01", "housing", 1_250_000, "rent, in cash"),
        ]

    def test_header_is_case_insensitive_and_note_is_optional(self) -> None:
        rows, errors = parse_csv(" Amount , DATE ,Category\n100,2026-11-10,food\n")

        assert errors == []
        assert (rows[0].amount, rows[0].note) == (100, "")

    def test_header_only(self) -> None:
        assert parse_csv("date,category,amount\n") == ([], [])

    @pytest.mark.parametrize("text", ["", "\n", " , \n"])
    def test_empty_file(self, text: str) -> None:
        with pytest.raises(ValidationError, match="The file is empty"):
            parse_csv(text)

    def test_missing_columns(self) -> None:
        with pytest.raises(ValidationError, match="Missing column: amount"):
            parse_csv("date,category\n")
        with pytest.raises(ValidationError, match="Missing columns: date, category, amount"):
            parse_csv("a,b\n1,2\n")

    def test_every_bad_row_is_reported_with_its_line_number(self) -> None:
        rows, errors = parse_csv(
            "date,category,amount,note\n"
            "2026-11-10,food,100,ok\n"
            "2026-02-30,food,100,\n"
            "2026-11-10,food,-5,\n"
            "2026-11-10,food,12.5,\n"
            "2026-11-10,,100,\n"
            "2026-11-10,food\n"
        )

        assert len(rows) == 1
        assert [error.split(":")[0] for error in errors] == [f"line {n}" for n in range(3, 8)]
        assert "Invalid date '2026-02-30'" in errors[0]
        assert "greater than zero" in errors[1]
        assert "Invalid amount '12.5'" in errors[2]
        assert "Category name cannot be empty" in errors[3]
        assert "Invalid amount ''" in errors[4]

    def test_malformed_csv(self) -> None:
        with pytest.raises(ValidationError, match="Not a valid CSV file"):
            parse_csv("date,category,amount\n2026-11-10,food," + "9" * 200_000 + "\n")


class TestImport:
    def test_import(
        self, transfer: TransferService, expenses: ExpenseService, tmp_path: Path
    ) -> None:
        path = csv_file(
            tmp_path,
            "date,category,amount,note\n2026-11-10,food,45000,lunch\n2026-11-01,housing,9,\n",
        )

        result = transfer.import_csv(path)

        assert (result.imported, result.skipped_duplicates, result.created_categories) == (2, 0, [])
        assert not result.dry_run
        assert [(e.category, e.amount, e.note) for e in expenses.find()] == [
            ("food", 45_000, "lunch"),
            ("housing", 9, ""),
        ]

    @pytest.mark.usefixtures("seeded")
    def test_export_then_import_round_trip(
        self, transfer: TransferService, tmp_path: Path, db_file: Path
    ) -> None:
        text, _ = transfer.export(ExportFormat.CSV)
        path = csv_file(tmp_path, text)
        other = db.connect(db_file.with_name("other.db"))
        try:
            TransferService(other).import_csv(path)
            assert TransferService(other).export(ExportFormat.CSV)[0].splitlines()[1:] == [
                '1,2026-11-01,housing,1250000,"rent, ""paid"" in cash"',
                "2,2026-11-10,food,45000,lunch plov",
                "3,2026-12-03,transport,7000,",
            ]
        finally:
            other.close()

    def test_invalid_rows_import_nothing(
        self, transfer: TransferService, expenses: ExpenseService, tmp_path: Path
    ) -> None:
        path = csv_file(
            tmp_path,
            "date,category,amount\n2026-11-10,food,100\nyesterday,food,100\n2026-11-10,food,0\n",
        )

        with pytest.raises(ValidationError) as excinfo:
            transfer.import_csv(path)

        message = str(excinfo.value)
        assert "2 invalid rows" in message
        assert "nothing was imported" in message
        assert "line 3: Invalid date 'yesterday'" in message
        assert "line 4: Amount must be greater than zero" in message
        assert expenses.find() == []

    def test_long_error_list_is_truncated(self, transfer: TransferService, tmp_path: Path) -> None:
        path = csv_file(tmp_path, "date,category,amount\n" + "bad,food,1\n" * 25)

        with pytest.raises(ValidationError) as excinfo:
            transfer.import_csv(path)

        message = str(excinfo.value)
        assert "25 invalid rows" in message
        assert "line 11:" in message
        assert "line 12:" not in message
        assert "... and 15 more" in message

    def test_unknown_categories_are_refused_by_default(
        self, transfer: TransferService, expenses: ExpenseService, tmp_path: Path
    ) -> None:
        path = csv_file(
            tmp_path,
            "date,category,amount\n2026-11-10,pets,1\n2026-11-10,food,1\n2026-11-10,Gifts,1\n",
        )

        with pytest.raises(
            ValidationError, match=r"Unknown categories in .*: gifts, pets"
        ) as excinfo:
            transfer.import_csv(path)

        assert "--create-categories" in str(excinfo.value)
        assert expenses.find() == []

    def test_create_categories(
        self, transfer: TransferService, expenses: ExpenseService, tmp_path: Path
    ) -> None:
        path = csv_file(tmp_path, "date,category,amount\n2026-11-10,Pets,1\n2026-11-11,pets,2\n")

        result = transfer.import_csv(path, create_categories=True)

        assert result.created_categories == ["pets"]
        assert [e.category for e in expenses.find()] == ["pets", "pets"]

    def test_dry_run_changes_nothing(
        self, transfer: TransferService, expenses: ExpenseService, tmp_path: Path
    ) -> None:
        path = csv_file(tmp_path, "date,category,amount\n2026-11-10,pets,1\n")

        result = transfer.import_csv(path, create_categories=True, dry_run=True)

        assert result.dry_run
        assert (result.imported, result.created_categories) == (1, ["pets"])
        assert expenses.find() == []
        with pytest.raises(NotFoundError):
            expenses.add("1", "pets")

    def test_reimport_duplicates_by_default(
        self, transfer: TransferService, expenses: ExpenseService, tmp_path: Path
    ) -> None:
        path = csv_file(tmp_path, "date,category,amount\n2026-11-10,food,1\n")

        transfer.import_csv(path)
        transfer.import_csv(path)

        assert len(expenses.find()) == 2

    def test_skip_duplicates(
        self, transfer: TransferService, expenses: ExpenseService, tmp_path: Path
    ) -> None:
        expenses.add("500", "transport", "bus", "2026-11-10")
        path = csv_file(
            tmp_path,
            "date,category,amount,note\n"
            "2026-11-10,transport,500,bus\n"
            "2026-11-10,transport,500,bus\n"
            "2026-11-10,transport,500,metro\n",
        )

        result = transfer.import_csv(path, skip_duplicates=True)

        # One stored "bus" cancels one row; the second identical ride is real.
        assert (result.imported, result.skipped_duplicates) == (2, 1)
        assert len(expenses.find()) == 3

        again = transfer.import_csv(path, skip_duplicates=True)
        assert (again.imported, again.skipped_duplicates) == (0, 3)

    def test_header_only_file_imports_nothing(
        self, transfer: TransferService, tmp_path: Path
    ) -> None:
        assert transfer.import_csv(csv_file(tmp_path, "date,category,amount\n")).imported == 0

    def test_missing_file(self, transfer: TransferService, tmp_path: Path) -> None:
        with pytest.raises(ValidationError, match="File not found"):
            transfer.import_csv(tmp_path / "nope.csv")
