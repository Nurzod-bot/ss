# spendr

[![CI](https://github.com/Nurzod-bot/ss/actions/workflows/ci.yml/badge.svg)](https://github.com/Nurzod-bot/ss/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A fast, friendly command-line expense tracker. Log what you spend, organise it by
category, set budgets, and see where the money went — without leaving the terminal.

<!-- TODO: record a demo and save it as docs/demo.gif -->
![spendr demo](docs/demo.gif)

## Features

- **Quick entry** — `spendr add 45000 food "lunch plov"` and you are done
- **Filtering** — list expenses by category, date range or month
- **Monthly summary** — totals and share per category, with a bar chart
- **Budgets** — per-category budgets plus an overall monthly limit, with savings,
  a daily allowance and red warnings above 90%
- **Categories** — add, rename and remove your own
- **Export and import** — CSV and JSON out, CSV in, with all-or-nothing validation
- **Exact money** — amounts are stored as integers, never floats
- **Friendly errors** — bad input gets a one-line explanation, not a traceback
- **Local and private** — everything lives in a single SQLite file on your machine

## Install

spendr needs Python 3.11 or newer. The easiest way to install it is with
[pipx](https://pipx.pypa.io):

```bash
git clone https://github.com/Nurzod-bot/ss.git
pipx install ./ss/spendr
```

Or straight from GitHub without cloning:

```bash
pipx install "git+https://github.com/Nurzod-bot/ss.git#subdirectory=spendr"
```

Then check that it works:

```bash
spendr --version
```

## Usage

Run `spendr --help`, or `spendr COMMAND --help`, for the full list of options.

### Add an expense

```bash
spendr add 45000 food "lunch plov" --date 2026-11-10
spendr add 12000 transport            # note is optional, date defaults to today
```

```
Added #1 · 45 000 UZS · food · 2026-11-10 · lunch plov
```

Amounts are whole numbers. Spaces and underscores may be used to group digits
(`"1 250 000"`, `1_250_000`).

### List expenses

```bash
spendr list
spendr list --month 2026-11
spendr list --category food --from 2026-11-01 --to 2026-11-15
spendr list --limit 10
```

```
                         Expenses
┏━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ ID ┃ Date       ┃ Category ┃ Amount (UZS) ┃ Note       ┃
┡━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│  2 │ 2026-11-11 │ housing  │    1 250 000 │ rent       │
│  1 │ 2026-11-10 │ food     │       45 000 │ lunch plov │
└────┴────────────┴──────────┴──────────────┴────────────┘
             2 expenses · total 1 295 000 UZS
```

### Edit and delete

```bash
spendr edit 1 --amount 50000 --note "lunch with Aziz"
spendr edit 1 --category other --date 2026-11-09
spendr edit 1 --note ""               # clear the note

spendr delete 1                       # asks for confirmation
spendr delete 1 --yes                 # skips it
```

### Summary

```bash
spendr summary                        # current month
spendr summary --month 2026-11
```

```
              Summary for 2026-11
┏━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Category  ┃ Expenses ┃ Amount (UZS) ┃  Share ┃
┡━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━┩
│ housing   │        1 │    1 250 000 │  87.9% │
│ food      │        2 │      165 000 │  11.6% │
│ transport │        1 │        7 000 │   0.5% │
├───────────┼──────────┼──────────────┼────────┤
│ Total     │        4 │    1 422 000 │ 100.0% │
└───────────┴──────────┴──────────────┴────────┘

  housing ██████████████████████████████ 87.9%
     food ████                           11.6%
transport █                               0.5%
```

### Categories

A new database starts with `food`, `transport`, `housing`, `utilities`, `health`,
`entertainment`, `shopping` and `other`.

```bash
spendr category list
spendr category add pets
spendr category rename food groceries   # expenses and budgets follow
spendr category remove pets             # only when it has no expenses
```

### Budgets

Set a budget per category, an overall limit for the month, or both. The overall
limit is independent of the category budgets, so the two do not have to add up.
All budget commands default to the current month.

```bash
spendr budget set food 1500000 --month 2026-11
spendr budget set food 1200000 --month 2026-11   # run again to change it
spendr budget total 5000000 --month 2026-11      # overall monthly limit

spendr budget remove food --month 2026-11
spendr budget remove --total --month 2026-11

spendr budget status
spendr budget status --month 2026-11
```

```
                           Budgets for 2026-11 (UZS)
┏━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Category ┃    Budget ┃     Spent ┃ Remaining ┃            Used ┃ Status      ┃
┡━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ food     │   175 000 │   165 000 │    10 000 │  █████████░ 94% │ near limit  │
│ health   │   300 000 │         0 │   300 000 │   ░░░░░░░░░░ 0% │ ok          │
│ housing  │ 1 200 000 │ 1 250 000 │   -50 000 │ ██████████ 104% │ over budget │
├──────────┼───────────┼───────────┼───────────┼─────────────────┼─────────────┤
│ Total    │ 1 675 000 │ 1 415 000 │   260 000 │                 │             │
└──────────┴───────────┴───────────┴───────────┴─────────────────┴─────────────┘
╭─ Highlights ──────────────────────────────────────────────╮
│ Overall budget   2 000 000 UZS                            │
│ Spent            1 422 000 UZS (71%)                      │
│ Left to spend    578 000 UZS                              │
│ Daily allowance  28 900 UZS per day for the next 20 days  │
│ Unallocated      325 000 UZS not assigned to any category │
│ Unbudgeted       7 000 UZS spent on transport             │
│ Over budget      housing                                  │
│ Above 90%        food                                     │
╰───────────────────────────────────────────────────────────╯
```

A category turns red once more than 90% of its budget is spent. For a past month
the panel shows what you **saved** instead of what is left to spend.

### Export

```bash
spendr export                                        # CSV to the terminal
spendr export --format csv --output expenses.csv
spendr export --format json --output november.json --month 2026-11
spendr export --output expenses.csv --force          # overwrite an existing file
```

`export` accepts the same `--category`, `--from`, `--to` and `--month` filters as
`list`.

### Import

```bash
spendr import expenses.csv
spendr import expenses.csv --dry-run             # check the file, change nothing
spendr import expenses.csv --create-categories   # add categories that are missing
spendr import expenses.csv --skip-duplicates     # safe to re-import the same file
```

The CSV needs a header row with `date`, `category` and `amount`; `note` is optional
and other columns are ignored:

```csv
date,category,amount,note
2026-11-10,food,45000,lunch plov
2026-11-01,housing,1250000,rent
```

An import is all-or-nothing: if any row is invalid, nothing is imported and every
problem is reported with its line number.

### Configuration

```bash
spendr config show             # currency and file locations
spendr config currency USD     # change the currency shown next to amounts
```

The currency defaults to `UZS`. The config file and the database live in your
user data directory:

| OS      | Location                                  |
|---------|-------------------------------------------|
| Linux   | `~/.local/share/spendr/`                  |
| macOS   | `~/Library/Application Support/spendr/`   |
| Windows | `%LOCALAPPDATA%\spendr\`                  |

Two environment variables override the paths, which is handy for testing or for
keeping separate ledgers:

| Variable        | Purpose                   |
|-----------------|---------------------------|
| `SPENDR_DB`     | Path of the database file |
| `SPENDR_CONFIG` | Path of the config file   |

```bash
SPENDR_DB=/tmp/demo.db spendr add 100 food
```

## Development

```bash
git clone https://github.com/Nurzod-bot/ss.git
cd ss/spendr
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Run the checks that CI runs:

```bash
ruff check .            # lint
ruff format --check .   # formatting
mypy                    # strict type checking
pytest --cov            # tests with coverage
```

Tests never touch your real data: every test runs against a temporary database
and config file.

## Project structure

```
spendr/
├── src/spendr/
│   ├── cli.py          # Typer commands: parse input, render output
│   ├── services.py     # business logic: validation, summaries, budgets
│   ├── transfer.py     # CSV/JSON export and CSV import
│   ├── repository.py   # all SQL queries
│   ├── db.py           # connection, schema, migrations
│   ├── models.py       # dataclasses shared by every layer
│   ├── formatting.py   # Rich tables, charts, currency formatting
│   ├── config.py       # settings and file locations
│   └── errors.py       # user-facing exception types
├── tests/              # pytest suite (unit + CLI)
├── pyproject.toml
└── LICENSE
```

The layers only depend downwards: `cli` → `services` / `transfer` → `repository`
→ `db`. Business logic never prints and SQL never leaves `repository.py`, which
keeps each layer testable on its own.

## Roadmap

- [ ] Recurring expenses
- [ ] Multiple currencies with conversion
- [ ] Income tracking
- [ ] Interactive TUI mode with [Textual](https://textual.textualize.io)

## License

[MIT](LICENSE)
