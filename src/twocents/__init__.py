"""twocents: exchange rates from Banca d'Italia.

Library usage::

    import datetime as dt
    import twocents

    rates = twocents.get_rates("USD", dt.date(2023, 1, 1), dt.date(2023, 1, 31))
    for rate in rates:
        print(rate.date, rate.currency_per_reference)

The command line interface lives in :mod:`twocents.cli` and needs the ``cli``
extra (``pip install 'twocents-xchange-rate[cli]'``).
"""

import logging
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version

from twocents.client import Language
from twocents.client import RatesClient
from twocents.errors import APIError
from twocents.errors import InvalidDateRangeError
from twocents.errors import TwocentsError
from twocents.exporters import CsvExporter
from twocents.exporters import Exporter
from twocents.exporters import JsonExporter
from twocents.models import REFERENCE_CURRENCIES
from twocents.models import Country
from twocents.models import Currency
from twocents.models import ExchangeConvention
from twocents.models import Fill
from twocents.models import Granularity
from twocents.models import Rate
from twocents.service import get_rates
from twocents.service import list_currencies


try:
    __version__ = version("twocents-xchange-rate")
except PackageNotFoundError:  # pragma: no cover - running from a raw checkout
    __version__ = "0.0.0-unknown"

# Libraries must not configure logging; callers opt in to see debug output.
logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = [
    "REFERENCE_CURRENCIES",
    "APIError",
    "Country",
    "CsvExporter",
    "Currency",
    "ExchangeConvention",
    "Exporter",
    "Fill",
    "Granularity",
    "InvalidDateRangeError",
    "JsonExporter",
    "Language",
    "Rate",
    "RatesClient",
    "TwocentsError",
    "__version__",
    "get_rates",
    "list_currencies",
]
