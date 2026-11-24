import datetime as dt
from pathlib import Path

import click

from twocents.cli.output import library_errors
from twocents.cli.output import output_options
from twocents.cli.output import verbose_option
from twocents.cli.output import write_records
from twocents.models import REFERENCE_CURRENCIES
from twocents.service import get_rates
from twocents.service import list_currencies


DATE = click.DateTime(formats=["%Y-%m-%d"])


def _upper(_ctx: click.Context, _param: click.Parameter, value: str) -> str:
    return value.upper()


@click.group()
def rates():
    """Get exchange rates from Banca d'Italia."""


@rates.command(name="list")
@verbose_option
@output_options
def list_command(fmt: str, file: Path | None):
    """List all available currencies from Banca d'Italia."""
    with library_errors():
        currencies = list_currencies()
    write_records(currencies, fmt, file)


@rates.command()
@verbose_option
@click.option(
    "--from",
    "currency",
    required=True,
    callback=_upper,
    help="ISO code of the currency to get rates for (e.g. USD).",
)
@click.option(
    "--to",
    "reference_currency",
    callback=_upper,
    default="EUR",
    show_default=True,
    help=(
        "Currency the rates are quoted against. Either --from or --to must "
        "be " + ", ".join(REFERENCE_CURRENCIES) + "."
    ),
)
@click.option(
    "--from-date",
    "start",
    type=DATE,
    metavar="YYYY-MM-DD",
    default=None,
    help="First day of the range (YYYY-MM-DD). Defaults to --to-date.",
)
@click.option(
    "--to-date",
    "end",
    type=DATE,
    metavar="YYYY-MM-DD",
    default=None,
    help="Last day of the range (YYYY-MM-DD). Defaults to today.",
)
@click.option(
    "--daily",
    "granularity",
    flag_value="daily",
    default=True,
    help="Daily rates (default).",
)
@click.option(
    "--monthly",
    "granularity",
    flag_value="monthly",
    help="Monthly averages.",
)
@click.option(
    "--yearly",
    "granularity",
    flag_value="yearly",
    help="Yearly averages.",
)
@click.option(
    "--fillup",
    "fill",
    flag_value="up",
    default=None,
    help="Fill days without a rate with the last earlier rate.",
)
@click.option(
    "--filldown",
    "fill",
    flag_value="down",
    help="Fill days without a rate with the first later rate.",
)
@click.option(
    "--fillmax",
    "fill",
    flag_value="max",
    help="Fill days without a rate with the larger of the two above.",
)
@output_options
def convert(
    currency: str,
    reference_currency: str,
    start: dt.datetime | None,
    end: dt.datetime | None,
    granularity: str,
    fill: str | None,
    fmt: str,
    file: Path | None,
):
    """Get exchange rates for a currency over a date range.

    Without --from-date and --to-date, only today's rate is returned.

    If --to is not EUR, USD or ITL (e.g. --from EUR --to KWD), the pair is
    fetched the other way round and every rate is inverted (1 / rate).
    """
    if (
        currency not in REFERENCE_CURRENCIES
        and reference_currency not in REFERENCE_CURRENCIES
    ):
        raise click.UsageError(
            f"Banca d'Italia only quotes against "
            f"{', '.join(REFERENCE_CURRENCIES)}: --from or --to must be "
            f"one of them, got {currency} and {reference_currency}."
        )
    if fill is not None and granularity != "daily":
        raise click.UsageError(
            "--fillup, --filldown and --fillmax only apply to --daily."
        )
    with library_errors():
        result = get_rates(
            currency,
            start.date() if start else None,
            end.date() if end else None,
            reference_currency=reference_currency,
            granularity=granularity,
            fill=fill,
        )
    write_records(result, fmt, file)
