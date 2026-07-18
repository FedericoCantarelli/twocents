from datetime import datetime
from enum import Enum
from typing import Any

import requests

from twocents.utils.pretty_print import print_verbose


class Language(Enum):
    """Enumeration for supported languages."""

    IT = "it"
    EN = "en"


def _exclude_fields(fields: list[str]):
    def decorator(func):
        def wrapper(*args, **kwargs):
            response = func(*args, **kwargs)
            if isinstance(response, dict):
                return {k: v for k, v in response.items() if k not in fields}
            return response

        return wrapper

    return decorator


def _check_response_code(func):
    def wrapper(*args, **kwargs):
        response = func(*args, **kwargs)
        if response.status_code != 200:
            raise Exception(f"Request failed with status code {response.status_code}")
        return response

    return wrapper


class RatesClient:
    def __init__(self, language: Language = Language.EN):
        self.base_url = (
            "https://tassidicambio.bancaditalia.it/terzevalute-wf-web/rest/v1.0"
        )
        self.language = language

    def _make_get_request(self, endpoint: str, headers: dict[str, str] | None = None):
        url = f"{self.base_url}/{endpoint}"
        if len(endpoint.split("&")) <= 1:
            url += f"?lang={self.language.value}"
        else:
            url += f"&lang={self.language.value}"
        print_verbose(f"Making GET request to URL: {url}")
        response = requests.get(url=url, headers=headers)
        print_verbose(f"Received response with status code: {response.status_code}")
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()

    def get_available_currencies(self) -> dict[str, Any]:
        headers = {"Accept": "application/json"}
        return self._make_get_request("currencies", headers=headers)

    @_exclude_fields(["resultsInfo"])
    def get_daily_exchange_rates(
        self,
        from_currency: str,
        to_currency: str,
        reference_date: datetime | None = None,
    ) -> dict[str, Any]:
        if reference_date is None:
            reference_date = datetime.now()
        headers = {"Accept": "application/json"}
        endpoint = f"dailyRates?referenceDate={reference_date.strftime('%Y-%m-%d')}"
        endpoint += f"&baseCurrencyIsoCode={from_currency}"
        endpoint += f"&currencyIsoCode={to_currency}"
        return self._make_get_request(endpoint, headers=headers)

    @_exclude_fields(["resultsInfo"])
    def get_avg_monthly_exchange_rates(
        self,
        from_currency: str,
        to_currency: str,
        month: int,
        year: int,
    ) -> dict[str, Any]:
        headers = {"Accept": "application/json"}
        endpoint = f"monthlyAverageRates?month={month}&year={year}"
        endpoint += f"&baseCurrencyIsoCode={from_currency}"
        endpoint += f"&currencyIsoCode={to_currency}"
        return self._make_get_request(endpoint, headers=headers)

    @_exclude_fields(["resultsInfo"])
    def get_avg_yearly_exchange_rates(
        self,
        from_currency: str,
        to_currency: str,
        year: int,
    ) -> dict[str, Any]:
        headers = {"Accept": "application/json"}
        endpoint = f"annualAverageRates?year={year}"
        endpoint += f"&baseCurrencyIsoCode={from_currency}"
        endpoint += f"&currencyIsoCode={to_currency}"
        return self._make_get_request(endpoint, headers=headers)

    @_exclude_fields(["resultsInfo"])
    def get_daily_exchange_rates_historical(
        self,
        from_currency: str,
        to_currency: str,
        from_date: datetime,
        to_date: datetime | None = None,
    ) -> dict[str, Any]:
        if to_date is None:
            to_date = datetime.now()
        headers = {"Accept": "application/json"}
        endpoint = f"dailyTimeSeries?startDate={from_date.strftime('%Y-%m-%d')}"
        endpoint += f"&endDate={to_date.strftime('%Y-%m-%d')}"
        endpoint += f"&baseCurrencyIsoCode={from_currency}"
        endpoint += f"&currencyIsoCode={to_currency}"
        return self._make_get_request(endpoint, headers=headers)


if __name__ == "__main__":
    client = RatesClient()
    rate = client.get_daily_exchange_rates_historical(
        "KWD", "EUR", from_date=datetime(2026, 7, 1), to_date=datetime(2026, 7, 18)
    )
    print(rate)
