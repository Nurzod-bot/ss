"""Export expenses to CSV or JSON and import them from CSV.

An import is all-or-nothing: every row is validated first, and the file is
only written to the database when no row has a problem.
"""

import csv
import io
import json
import sqlite3
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path

from spendr.errors import SpendrError, ValidationError
from spendr.models import Expense
from spendr.repository import CategoryRepository, ExpenseRepository
from spendr.services import (
    ExpenseService,
    clean_category_name,
    clean_note,
    parse_amount,
    parse_date,
)

EXPORT_COLUMNS = ("id", "date", "category", "amount", "note")
REQUIRED_IMPORT_COLUMNS = ("date", "category", "amount")
MAX_REPORTED_ERRORS = 10


class ExportFormat(StrEnum):
    CSV = "csv"
    JSON = "json"


@dataclass(frozen=True, slots=True)
class ImportRow:
    line: int
    spent_on: date
    category: str
    amount: int
    note: str


@dataclass(frozen=True, slots=True)
class ImportResult:
    imported: int
    skipped_duplicates: int
    created_categories: list[str]
    dry_run: bool


def _record(expense: Expense) -> dict[str, int | str]:
    return {
        "id": expense.id,
        "date": expense.spent_on.isoformat(),
        "category": expense.category,
        "amount": expense.amount,
        "note": expense.note,
    }


def to_csv(expenses: Sequence[Expense]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=EXPORT_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(_record(expense) for expense in expenses)
    return buffer.getvalue()


def to_json(expenses: Sequence[Expense]) -> str:
    records = [_record(expense) for expense in expenses]
    return json.dumps(records, indent=2, ensure_ascii=False) + "\n"


def serialize(expenses: Sequence[Expense], fmt: ExportFormat) -> str:
    return to_json(expenses) if fmt is ExportFormat.JSON else to_csv(expenses)


def write_text(path: Path, text: str, *, overwrite: bool = False) -> None:
    """Write an export file, refusing to replace an existing one unless asked."""
    if path.exists() and not overwrite:
        raise ValidationError(f"{path} already exists. Use --force to overwrite it.")
    try:
        # newline="" keeps the line endings exactly as serialized on every OS.
        path.write_text(text, encoding="utf-8", newline="")
    except OSError as exc:
        raise ValidationError(f"Cannot write {path}: {exc.strerror}.") from exc


def read_text(path: Path) -> str:
    try:
        # utf-8-sig also accepts the byte-order mark that Excel adds.
        return path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        raise ValidationError(f"File not found: {path}") from None
    except OSError as exc:
        raise ValidationError(f"Cannot read {path}: {exc.strerror}.") from exc
    except UnicodeDecodeError:
        raise ValidationError(f"{path} is not a UTF-8 text file.") from None


def parse_csv(text: str) -> tuple[list[ImportRow], list[str]]:
    """Parse CSV text into rows plus a list of ``line N: problem`` messages.

    The header must contain ``date``, ``category`` and ``amount``; ``note`` is
    optional and any other column (such as ``id``) is ignored.
    """
    reader = csv.reader(io.StringIO(text, newline=""))
    try:
        header = next(reader, None)
        if header is None or not any(cell.strip() for cell in header):
            raise ValidationError("The file is empty: expected a header row.")
        columns = [cell.strip().lower() for cell in header]
        missing = [name for name in REQUIRED_IMPORT_COLUMNS if name not in columns]
        if missing:
            raise ValidationError(
                f"Missing column{'s' if len(missing) != 1 else ''}: {', '.join(missing)}. "
                "The header row must contain date, category and amount (note is optional)."
            )

        rows: list[ImportRow] = []
        errors: list[str] = []
        for cells in reader:
            if not any(cell.strip() for cell in cells):
                continue
            values = dict(zip(columns, cells, strict=False))
            try:
                rows.append(
                    ImportRow(
                        line=reader.line_num,
                        spent_on=parse_date(values.get("date", "")),
                        category=clean_category_name(values.get("category", "")),
                        amount=parse_amount(values.get("amount", "")),
                        note=clean_note(values.get("note", "")),
                    )
                )
            except SpendrError as exc:
                errors.append(f"line {reader.line_num}: {exc}")
    except csv.Error as exc:
        raise ValidationError(f"Not a valid CSV file (line {reader.line_num}: {exc}).") from exc
    return rows, errors


class TransferService:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._expenses = ExpenseRepository(conn)
        self._categories = CategoryRepository(conn)
        self._expense_service = ExpenseService(conn)

    def export(
        self,
        fmt: ExportFormat,
        *,
        category: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        month: str | None = None,
    ) -> tuple[str, int]:
        """Serialize matching expenses, oldest first. Returns the text and the count."""
        expenses = self._expense_service.find(
            category=category, date_from=date_from, date_to=date_to, month=month
        )
        expenses.sort(key=lambda expense: (expense.spent_on, expense.id))
        return serialize(expenses, fmt), len(expenses)

    def import_csv(
        self,
        path: Path,
        *,
        create_categories: bool = False,
        skip_duplicates: bool = False,
        dry_run: bool = False,
    ) -> ImportResult:
        rows, errors = parse_csv(read_text(path))
        if errors:
            shown = errors[:MAX_REPORTED_ERRORS]
            if len(errors) > len(shown):
                shown.append(f"... and {len(errors) - len(shown)} more")
            count = f"{len(errors)} invalid row{'s' if len(errors) != 1 else ''}"
            raise ValidationError(
                f"{count} in {path}, nothing was imported.\n  " + "\n  ".join(shown)
            )

        known = {category.name: category.id for category in self._categories.list_all()}
        unknown = sorted({row.category for row in rows} - known.keys())
        if unknown and not create_categories:
            raise ValidationError(
                f"Unknown categor{'ies' if len(unknown) != 1 else 'y'} in {path}: "
                f"{', '.join(unknown)}. Nothing was imported. "
                "Re-run with --create-categories to add them."
            )

        skipped = 0
        if skip_duplicates:
            existing = Counter(
                (e.spent_on, e.category, e.amount, e.note) for e in self._expenses.find()
            )
            fresh: list[ImportRow] = []
            for row in rows:
                key = (row.spent_on, row.category, row.amount, row.note)
                if existing[key] > 0:
                    # Each stored expense cancels out one identical row, so
                    # genuine repeats (two bus rides on one day) still import.
                    existing[key] -= 1
                    skipped += 1
                else:
                    fresh.append(row)
            rows = fresh

        if not dry_run:
            for name in unknown:
                known[name] = self._categories.add(name).id
            self._expenses.add_many(
                [(row.amount, known[row.category], row.note, row.spent_on) for row in rows]
            )
        return ImportResult(
            imported=len(rows),
            skipped_duplicates=skipped,
            created_categories=unknown,
            dry_run=dry_run,
        )
