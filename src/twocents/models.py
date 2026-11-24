"""Typed models for the data returned by the Banca d'Italia API."""

import dataclasses
import datetime as dt
import decimal
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any
from typing import Protocol


REFERENCE_CURRENCIES = ("EUR", "USD", "ITL")
"""Currencies the API can quote rates against (its ``currencyIsoCode``)."""

INVERTED_PRECISION = 6
"""Significant digits kept by :meth:`Rate.inverted`."""


class Granularity(StrEnum):
    """Time granularity of a rate."""

    DAILY = "daily"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class Fill(StrEnum):
    """How to fill the days without a published daily rate."""

    UP = "up"
    """Use the last earlier day with a rate."""

    DOWN = "down"
    """Use the first later day with a rate."""

    MAX = "max"
    """Use the larger of the ``UP`` and ``DOWN`` candidates."""


class ExchangeConvention(StrEnum):
    """How to read :attr:`Rate.value`.

    The API quotes some currencies "certain for uncertain" and others the
    other way around, so the same pair can come back in either direction.
    """

    CURRENCY_PER_REFERENCE = "C"
    """``value`` units of the currency buy 1 unit of the reference currency."""

    REFERENCE_PER_CURRENCY = "I"
    """``value`` units of the reference currency buy 1 unit of the currency."""


class Record(Protocol):
    """Anything the exporters know how to serialise."""

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        ...

    def to_row(self) -> dict[str, Any]:
        """Return a flat representation, suitable for a CSV row."""
        ...


def _parse_date(value: str | None) -> dt.date | None:
    return dt.date.fromisoformat(value) if value else None


def _iso(value: dt.date | None) -> str | None:
    return value.isoformat() if value else None


@dataclass(frozen=True, slots=True)
class Country:
    """A country that uses (or used) a currency over a period of time."""

    name: str
    iso_code: str | None
    valid_from: dt.date | None
    valid_to: dt.date | None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "Country":
        """Build a Country from an item of a currency's ``countries`` list."""
        return cls(
            name=data["country"],
            iso_code=data.get("countryISO"),
            valid_from=_parse_date(data.get("validityStartDate")),
            valid_to=_parse_date(data.get("validityEndDate")),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "name": self.name,
            "iso_code": self.iso_code,
            "valid_from": _iso(self.valid_from),
            "valid_to": _iso(self.valid_to),
        }


@dataclass(frozen=True, slots=True)
class Currency:
    """A currency listed by Banca d'Italia."""

    iso_code: str
    name: str
    countries: tuple[Country, ...] = ()

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "Currency":
        """Build a Currency from an item of the ``currencies`` response."""
        return cls(
            iso_code=data["isoCode"],
            name=data["name"],
            countries=tuple(
                Country.from_api(c) for c in data.get("countries") or ()
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "iso_code": self.iso_code,
            "name": self.name,
            "countries": [c.to_dict() for c in self.countries],
        }

    def to_row(self) -> dict[str, Any]:
        """Return a flat representation; countries are joined by ``; ``."""
        return {
            "iso_code": self.iso_code,
            "name": self.name,
            "countries": "; ".join(c.name for c in self.countries),
        }


@dataclass(frozen=True, slots=True)
class Rate:
    """An exchange rate between a currency and a reference currency.

    Attributes:
        currency: ISO code of the quoted currency (e.g. ``"USD"``).
        reference_currency: ISO code it is quoted against (EUR, USD or ITL).
        value: The rate as published; see ``convention`` for its direction.
        convention: How to read ``value``.
        granularity: Whether this is a daily rate or a monthly/yearly average.
        date: The reference day, or the first day of the averaged period.
    """

    currency: str
    reference_currency: str
    value: Decimal
    convention: ExchangeConvention
    granularity: Granularity
    date: dt.date

    @property
    def currency_per_reference(self) -> Decimal:
        """Units of ``currency`` needed to buy 1 ``reference_currency``."""
        if self.convention is ExchangeConvention.CURRENCY_PER_REFERENCE:
            return self.value
        return 1 / self.value

    @property
    def reference_per_currency(self) -> Decimal:
        """Units of ``reference_currency`` needed to buy 1 ``currency``."""
        if self.convention is ExchangeConvention.REFERENCE_PER_CURRENCY:
            return self.value
        return 1 / self.value

    def inverted(self) -> "Rate":
        """Return the same rate seen from the other side of the pair.

        ``currency`` and ``reference_currency`` are swapped and ``value``
        becomes ``1 / value``, rounded to ``INVERTED_PRECISION`` significant
        digits; ``convention`` keeps its meaning.
        """
        with decimal.localcontext(prec=INVERTED_PRECISION):
            value = 1 / self.value
        return dataclasses.replace(
            self,
            currency=self.reference_currency,
            reference_currency=self.currency,
            value=value,
        )

    @classmethod
    def from_api(
        cls,
        data: dict[str, Any],
        *,
        reference_currency: str,
        granularity: Granularity,
        defaults: dict[str, Any] | None = None,
    ) -> "Rate":
        """Build a Rate from an item of a ``rates`` response list.

        Args:
            data (dict[str, Any]): One item of the response's ``rates``.
            reference_currency (str): The ``currencyIsoCode`` requested.
            granularity (Granularity): Which endpoint the item came from.
            defaults (dict[str, Any] | None): Fallback fields, used for the
                daily time series whose items omit ``isoCode`` and
                ``exchangeConventionCode`` (they are in ``resultsInfo``).
        """
        merged = {**(defaults or {}), **data}
        if granularity is Granularity.DAILY:
            date = dt.date.fromisoformat(merged["referenceDate"])
        else:
            date = dt.date(merged["year"], merged.get("month") or 1, 1)
        return cls(
            currency=merged["isoCode"],
            reference_currency=reference_currency,
            value=Decimal(merged["avgRate"]),
            convention=ExchangeConvention(merged["exchangeConventionCode"]),
            granularity=granularity,
            date=date,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "currency": self.currency,
            "reference_currency": self.reference_currency,
            "date": self.date.isoformat(),
            "granularity": self.granularity.value,
            "value": str(self.value),
            "convention": self.convention.value,
        }

    def to_row(self) -> dict[str, Any]:
        """Return a flat representation, suitable for a CSV row."""
        return self.to_dict()
