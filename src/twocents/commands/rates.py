import os

import click

from twocents.exporters.json_exporter import JsonExporter
from twocents.exporters.std_out import StdOutExporter
from twocents.rates.client import RatesClient
from twocents.utils import parse_datetime
from twocents.utils import safe_parse_datetime


@click.group()
def rates():
    """Get exchange rates from Banca d'Italia."""


@rates.command()
@click.option(
    "--format",
    type=str,
    required=False,
    default=None,
    help="""Get the output in a specified format.
    If not specified, the output is printed to stdout.
    Supported formats: 'json', 'csv'.""",
)
@click.option(
    "--file",
    type=click.Path(),
    required=False,
    default=None,
    help="Export the output to a file. Required only with --format option.",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Show verbose output.",
    required=False,
    default=False,
)
def list(format, file, verbose):
    """List all available currencies from Banca d'Italia."""
    if format is not None:
        if format not in ["json", "csv"]:
            raise click.BadParameter(
                f"Invalid format: {format}. Expected 'json' or 'csv'."
            )
        if not file:
            raise click.BadParameter(
                "The --file option is required when using the --format option."
            )
    # Set verbose mode if the --verbose flag is set
    if verbose:
        os.environ["VERBOSE"] = "1"
    client: RatesClient = RatesClient()
    output = client.get_available_currencies()
    if format is not None:
        if format == "json":
            exporter = JsonExporter(output)
            exporter.export(file)
        # elif format == "csv":
        #     from twocents.exporters.csv import CsvExporter

        #     exporter = CsvExporter(currencies)
        #     exporter.export()
    else:
        exporter = StdOutExporter(output)
        exporter.export()


@rates.command()
@click.option(
    "--verbose",
    is_flag=True,
    help="Show verbose output.",
    required=False,
    default=False,
)
@click.option(
    "--format",
    type=str,
    required=False,
    default=None,
    help="Get the output in a specified format.",
)
@click.option(
    "--from",
    "from_currency",
    type=str,
    required=True,
    help="Get the exchange rate from a specific currency.",
)
@click.option(
    "--to",
    "to_currency",
    type=str,
    required=False,
    default="EUR",
    help="Get the exchange rate to a specific currency. Defaults to EUR.",
)
@click.option(
    "--from-date",
    type=str,
    required=True,
    help="Get the exchange rate from a specific date (YYYY-MM-DD).",
)
@click.option(
    "--to-date",
    type=str,
    required=False,
    default=None,
    help="""Get the exchange rate to a specific date (YYYY-MM-DD).
    If not specified, the current date will be used.""",
)
@click.option(
    "--daily",
    is_flag=True,
    required=False,
    default=True,
    help="Get exchange rates with a daily granularity.",
)
@click.option(
    "--monthly",
    is_flag=True,
    required=False,
    default=False,
    help="Get exchange rates with a monthly granularity.",
)
@click.option(
    "--yearly",
    is_flag=True,
    required=False,
    default=False,
    help="Get exchange rates with a yearly granularity.",
)
@click.option(
    "--file",
    type=click.Path(),
    required=False,
    default=None,
    help="Export the output to a file. Required only with --format option.",
)
def convert(
    verbose: bool,
    from_currency: str,
    to_currency: str,
    from_date: str,
    to_date: str | None,
    format: str | None,
    file: str | None,
    daily: bool,
    monthly: bool,
    yearly: bool,
):
    """Get exchange rates from Banca d'Italia."""
    if format is not None:
        if format not in ["json", "csv"]:
            raise click.BadParameter(
                f"Invalid format: {format}. Expected 'json' or 'csv'."
            )
        if not file:
            raise click.BadParameter(
                "The --file option is required when using the --format option."
            )

    if verbose:
        os.environ["VERBOSE"] = "1"

    client: RatesClient = RatesClient()

    if daily:
        try:
            parsed_from_date = parse_datetime(from_date)
        except ValueError as e:
            raise click.BadParameter(
                f"Got --from-date: {from_date}. Expected format: 'YYYY-MM-DD'"
            ) from e
        parsed_to_date = safe_parse_datetime(to_date)
        output = client.get_daily_exchange_rates_historical(
            from_currency=from_currency,
            to_currency=to_currency,
            from_date=parsed_from_date,
            to_date=parsed_to_date,
        )
    if format is not None:
        if format == "json":
            exporter = JsonExporter(output)
            exporter.export(file)
        # elif format == "csv":
        #     from twocents.exporters.csv import CsvExporter

        #     exporter = CsvExporter(currencies)
        #     exporter.export()
    else:
        exporter = StdOutExporter(output)
        exporter.export()
