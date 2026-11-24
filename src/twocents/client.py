"""Low-level client for the Banca d'Italia exchange rates REST API.

Each method maps to exactly one endpoint and returns typed models. For date
ranges at any granularity, use :func:`twocents.get_rates` instead.
"""

import datetime as dt
import logging
from enum import Enum
from typing import Any

import requests

from twocents.errors import APIError
from twocents.models import Currency
from twocents.models import Granularity
from twocents.models import Rate


logger = logging.getLogger(__name__)

BASE_URL = "https://tassidicambio.bancaditalia.it/terzevalute-wf-web/rest/v1.0"
DEFAULT_TIMEOUT = 30.0


class Language(Enum):
    """Language of descriptive fields (currency and country names)."""

    IT = "it"
    EN = "en"


class RatesClient:
    """Thin wrapper around the Banca d'Italia endpoints.

    Example:
        >>> client = RatesClient()
        >>> client.get_daily_time_series("USD", dt.date(2023, 1, 2))
        [Rate(currency='USD', reference_currency='EUR', ...)]
    """

    def __init__(
        self,
        language: Language = Language.EN,
        *,
        session: requests.Session | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        base_url: str = BASE_URL,
    ):
        """Init RatesClient.

        Args:
            language (Language): Language for currency/country names.
            session (requests.Session | None): Session to reuse; a new one is
                created if omitted.
            timeout (float): Seconds to wait for each request.
            base_url (str): API root, overridable for testing.
        """
        self.language = language
        self.timeout = timeout
        self.base_url = base_url.rstrip("/")
        self._session = session or requests.Session()

    def _get(self, endpoint: str, **params: Any) -> dict[str, Any]:
        url = f"{self.base_url}/{endpoint}"
        params["lang"] = self.language.value
        logger.debug("GET %s %s", url, params)
        try:
            response = self._session.get(
                url,
                params=params,
                headers={"Accept": "application/json"},
                timeout=self.timeout,
            )
        except requests.RequestException as e:
            raise APIError(str(e)) from e
        logger.debug("-> HTTP %s", response.status_code)
        if response.status_code != 200:
            raise APIError(response.text.strip(), response.status_code)
        return response.json()

    def _rates(
        self,
        endpoint: str,
        granularity: Granularity,
        reference_currency: str,
        **params: Any,
    ) -> list[Rate]:
        payload = self._get(
            endpoint, currencyIsoCode=reference_currency, **params
        )
        info = payload.get("resultsInfo") or {}
        return [
            Rate.from_api(
                item,
                reference_currency=reference_currency,
                granularity=granularity,
                defaults=info,
            )
            for item in payload.get("rates") or ()
        ]

    def get_currencies(self) -> list[Currency]:
        """Return every currency known to Banca d'Italia."""
        payload = self._get("currencies")
        return [Currency.from_api(c) for c in payload.get("currencies") or ()]

    def get_daily_rates(
        self,
        reference_date: dt.date,
        currency: str | None = None,
        reference_currency: str = "EUR",
    ) -> list[Rate]:
        """Return the rates published on a single day.

        Args:
            reference_date (dt.date): The day to look up.
            currency (str | None): Restrict to one currency; all if omitted.
            reference_currency (str): EUR, USD or ITL.
        """
        params: dict[str, Any] = {"referenceDate": reference_date.isoformat()}
        if currency:
            params["baseCurrencyIsoCode"] = currency
        return self._rates(
            "dailyRates", Granularity.DAILY, reference_currency, **params
        )

    def get_daily_time_series(
        self,
        currency: str,
        start: dt.date,
        end: dt.date | None = None,
        reference_currency: str = "EUR",
    ) -> list[Rate]:
        """Return one rate per business day between ``start`` and ``end``.

        Args:
            currency (str): ISO code of the quoted currency.
            start (dt.date): First day (inclusive).
            end (dt.date | None): Last day (inclusive); defaults to today.
            reference_currency (str): EUR, USD or ITL.
        """
        return self._rates(
            "dailyTimeSeries",
            Granularity.DAILY,
            reference_currency,
            startDate=start.isoformat(),
            endDate=(end or dt.date.today()).isoformat(),
            baseCurrencyIsoCode=currency,
        )

    def get_monthly_average(
        self,
        year: int,
        month: int,
        currency: str | None = None,
        reference_currency: str = "EUR",
    ) -> list[Rate]:
        """Return the average rates for one month.

        Args:
            year (int): Year.
            month (int): Month (1-12).
            currency (str | None): Restrict to one currency; all if omitted.
            reference_currency (str): EUR, USD or ITL.
        """
        params: dict[str, Any] = {"year": year, "month": month}
        if currency:
            params["baseCurrencyIsoCode"] = currency
        return self._rates(
            "monthlyAverageRates",
            Granularity.MONTHLY,
            reference_currency,
            **params,
        )

    def get_annual_average(
        self,
        year: int,
        currency: str | None = None,
        reference_currency: str = "EUR",
    ) -> list[Rate]:
        """Return the average rates for one year.

        Args:
            year (int): Year.
            currency (str | None): Restrict to one currency; all if omitted.
            reference_currency (str): EUR, USD or ITL.
        """
        params: dict[str, Any] = {"year": year}
        if currency:
            params["baseCurrencyIsoCode"] = currency
        return self._rates(
            "annualAverageRates",
            Granularity.YEARLY,
            reference_currency,
            **params,
        )
