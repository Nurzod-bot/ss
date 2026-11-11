from typer.testing import CliRunner

from spendr import __version__
from spendr.cli import app

runner = CliRunner()


def test_version_flag_prints_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.output.strip() == f"spendr {__version__}"


def test_help_describes_the_app() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Track your expenses" in result.output
