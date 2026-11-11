"""Typer commands. This module only parses input and renders output;
business logic lives in :mod:`spendr.services`."""

from typing import Annotated

import typer

from spendr import __version__

app = typer.Typer(
    name="spendr",
    help="Track your expenses from the terminal.",
    no_args_is_help=True,
    add_completion=False,
    # User errors are reported as friendly messages, so never dump local variables.
    pretty_exceptions_show_locals=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"spendr {__version__}")
        raise typer.Exit


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            help="Show the version and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """Track your expenses from the terminal."""
