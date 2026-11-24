"""Helpers shared by CLI commands: verbosity, error mapping, output."""

import logging
import sys
from collections.abc import Callable
from collections.abc import Generator
from collections.abc import Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import click

from twocents.errors import InvalidDateRangeError
from twocents.errors import TwocentsError
from twocents.exporters import EXPORTERS
from twocents.models import Record


def _enable_verbose(ctx: click.Context, _param: Any, value: bool) -> None:
    if not value:
        return
    logger = logging.getLogger("twocents")
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(message)s"))
    previous_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    def restore() -> None:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)

    ctx.call_on_close(restore)


def verbose_option[F: Callable[..., Any]](f: F) -> F:
    """Add ``--verbose``: log HTTP requests to stderr."""
    return click.option(
        "--verbose",
        is_flag=True,
        expose_value=False,
        is_eager=True,
        callback=_enable_verbose,
        help="Log the requests made to stderr.",
    )(f)


def output_options[F: Callable[..., Any]](f: F) -> F:
    """Add ``--format`` and ``--file``."""
    f = click.option(
        "--file",
        type=click.Path(dir_okay=False, path_type=Path),
        default=None,
        help="Write the output to this file instead of stdout.",
    )(f)
    return click.option(
        "--format",
        "fmt",
        type=click.Choice(sorted(EXPORTERS), case_sensitive=False),
        default="json",
        show_default=True,
        help="Output format.",
    )(f)


@contextmanager
def library_errors() -> Generator[None]:
    """Turn library exceptions into clean click errors (no traceback)."""
    try:
        yield
    except InvalidDateRangeError as e:
        raise click.UsageError(str(e)) from e
    except TwocentsError as e:
        raise click.ClickException(str(e)) from e


def write_records(records: Sequence[Record], fmt: str, file: Path | None):
    """Write records with the chosen exporter, to ``file`` or stdout."""
    exporter = EXPORTERS[fmt.lower()]()
    if file is None:
        exporter.dump(records, sys.stdout)
        return
    try:
        exporter.export(records, file)
    except OSError as e:
        raise click.FileError(str(file), hint=e.strerror) from e
