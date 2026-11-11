# spendr

A fast, friendly command-line expense tracker. Work in progress — full docs land with the first release.

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

ruff check . && ruff format --check .
mypy
pytest --cov
```
