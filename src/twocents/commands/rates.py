import os

import click

from twocents.exporters.std_out import StdOutExporter
from twocents.rates.client import Language
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
def rates(list: bool, verbose: bool, format: str | None):
    """Get exchange rates from Banca d'Italia."""
    if verbose:
        os.environ["VERBOSE"] = "1"
    if list:
        client = RatesClient(language=Language.IT)
        currencies = client.get_available_currencies()
    if format:
        print("Not implemented")
    else:
        exporter = StdOutExporter()
        exporter.export(currencies)
