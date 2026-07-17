import os

import click

from twocents.exporters.json_exporter import JsonExporter
from twocents.exporters.std_out import StdOutExporter
from twocents.rates.client import RatesClient


@click.command()
@click.option("--list", is_flag=True, help="Show all available exchange rates.")
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
    "--from-currency",
    type=str,
    required=False,
    default=None,
    help="Get the exchange rate from a specific currency.",
)
@click.option(
    "--to-currency",
    type=str,
    required=False,
    default=None,
    help="Get the exchange rate to a specific currency.",
)
@click.option(
    "--day",
    type=str,
    required=False,
    default=None,
    help="Get the exchange rate for a specific day (YYYY-MM-DD).",
)
@click.option(
    "--file",
    type=click.Path(),
    required=False,
    default=None,
    help="Export the output to a file. Required onl with --format option.",
)
def rates(
    list: bool,
    verbose: bool,
    from_currency: str,
    to_currency: str,
    format: str | None,
    file: str | None,
    day: str | None,
):
    """Get exchange rates from Banca d'Italia."""
    assert format is None or format in ["json", "csv"], (
        "Invalid format. Use 'json' or 'csv'."
    )
    if format:
        assert file, "The --file option is required when using the --format option."
    if verbose:
        os.environ["VERBOSE"] = "1"
    if list:
        client = RatesClient()
        currencies = client.get_available_currencies()
    elif from_currency and to_currency:
        client = RatesClient()
        currencies = client.get_daily_exchange_rates(
            from_currency=from_currency, to_currency=to_currency
        )

    if format is not None:
        if format == "json":
            exporter = JsonExporter(currencies)
            exporter.export(file)
        # elif format == "csv":
        #     from twocents.exporters.csv import CsvExporter

        #     exporter = CsvExporter(currencies)
        #     exporter.export()
    else:
        exporter = StdOutExporter(currencies)
        exporter.export()
