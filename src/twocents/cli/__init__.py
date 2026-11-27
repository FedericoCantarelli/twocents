"""Command line interface for twocents (entry point: ``tc``).

Requires the ``cli`` extra: ``pip install 'twocents-xchange-rate[cli]'``.
"""

try:
    import click
except ModuleNotFoundError as e:  # pragma: no cover - depends on install
    raise SystemExit(
        "The twocents CLI requires click. Install it with:\n"
        "    pip install 'twocents-xchange-rate[cli]'\n"
        "or\n"
        "    uv tool install 'twocents-xchange-rate[cli]'"
    ) from e

from twocents.cli.rates import rates
from twocents.cli.version import version


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def main():
    """Fetch currency exchange rates from Banca d'Italia."""


main.add_command(version)
main.add_command(rates)

__all__ = ["main"]
