"""Builders for API payloads, shaped like real Banca d'Italia responses."""

from typing import Any


NOTICE = "DISCLAIMER: ..."


def currencies_payload() -> dict[str, Any]:
    return {
        "resultsInfo": {"totalRecords": 2, "notice": NOTICE},
        "currencies": [
            {
                "countries": [
                    {
                        "currencyISO": "USD",
                        "country": "UNITED STATES",
                        "countryISO": "US",
                        "validityStartDate": "1918-01-01",
                        "validityEndDate": None,
                    },
                    {
                        "currencyISO": "USD",
                        "country": "ECUADOR",
                        "countryISO": None,
                        "validityStartDate": None,
                        "validityEndDate": None,
                    },
                ],
                "isoCode": "USD",
                "name": "U.S. Dollar",
                "graph": True,
            },
            {
                "countries": [],
                "isoCode": "XAU",
                "name": "Gold, Ounce",
                "graph": False,
            },
        ],
    }


def daily_series_payload(
    rates: list[tuple[str, str]],
    iso_code: str = "USD",
    convention: str = "C",
) -> dict[str, Any]:
    """``dailyTimeSeries``: rows lack isoCode/convention (in resultsInfo)."""
    info: dict[str, Any] = {"totalRecords": len(rates), "notice": NOTICE}
    if rates:
        info |= {
            "currency": "Some Currency",
            "isoCode": iso_code,
            "uicCode": "001",
            "exchangeConventionCode": convention,
        }
    return {
        "resultsInfo": info,
        "rates": [
            {
                "referenceDate": day,
                "avgRate": value,
                "exchangeConvention": "Foreign currency amount for 1 Euro.",
            }
            for day, value in rates
        ],
    }


def _full_rate(iso_code: str, value: str, convention: str) -> dict[str, Any]:
    return {
        "country": "SOMEWHERE",
        "currency": "Some Currency",
        "isoCode": iso_code,
        "uicCode": "001",
        "avgRate": value,
        "exchangeConvention": "...",
        "exchangeConventionCode": convention,
    }


def daily_rates_payload(
    day: str, value: str = "1.0545", iso_code: str = "USD", convention="C"
) -> dict[str, Any]:
    row = _full_rate(iso_code, value, convention) | {"referenceDate": day}
    return {"resultsInfo": {"totalRecords": 1}, "rates": [row]}


def monthly_payload(
    year: int,
    month: int,
    value: str = "1.0769",
    iso_code: str = "USD",
    convention: str = "C",
) -> dict[str, Any]:
    row = _full_rate(iso_code, value, convention)
    row |= {"year": year, "month": month}
    return {"resultsInfo": {"totalRecords": 1}, "rates": [row]}


def yearly_payload(
    year: int,
    value: str = "1.0530",
    iso_code: str = "USD",
    convention: str = "C",
) -> dict[str, Any]:
    row = _full_rate(iso_code, value, convention) | {"year": year}
    return {"resultsInfo": {"totalRecords": 1}, "rates": [row]}


EMPTY = {"resultsInfo": {"totalRecords": 0}, "rates": []}
