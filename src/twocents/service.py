"""High-level helpers: the recommended entry points for library users."""

import bisect
import dataclasses
import datetime as dt
from collections.abc import Iterable
from collections.abc import Iterator

from twocents.client import RatesClient
from twocents.errors import InvalidDateRangeError
from twocents.models import REFERENCE_CURRENCIES
from twocents.models import Currency
from twocents.models import Fill
from twocents.models import Granularity
from twocents.models import Rate


FILL_WINDOW = dt.timedelta(days=14)
"""How far outside the range to look for a rate when filling gaps."""


def list_currencies(client: RatesClient | None = None) -> list[Currency]:
    """Return every currency known to Banca d'Italia.

    Args:
        client (RatesClient | None): Client to use; a default one if omitted.
    """
    return (client or RatesClient()).get_currencies()


def months_between(start: dt.date, end: dt.date) -> Iterator[tuple[int, int]]:
    """Yield every ``(year, month)`` touched by ``[start, end]``, in order."""
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        yield year, month
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)


def days_between(start: dt.date, end: dt.date) -> Iterator[dt.date]:
    """Yield every day of ``[start, end]``, in order."""
    day = start
    while day <= end:
        yield day
        day += dt.timedelta(days=1)


def fill_rates(
    rates: Iterable[Rate], start: dt.date, end: dt.date, fill: Fill | str
) -> list[Rate]:
    """Return one daily rate per day of ``[start, end]``, filling the gaps.

    A day without a rate gets a copy of a neighbouring rate, dated that
    day. ``rates`` may extend outside the range, to provide neighbours for
    its first and last days. Days with no candidate are left out.

    Args:
        rates (Iterable[Rate]): Daily rates of a single currency pair.
        start (dt.date): First day of the range (inclusive).
        end (dt.date): Last day of the range (inclusive).
        fill (Fill | str): ``up`` (previous rate), ``down`` (next rate) or
            ``max`` (the larger of the two).
    """
    fill = Fill(fill)
    by_date = {rate.date: rate for rate in rates}
    known = sorted(by_date)
    filled = []
    for day in days_between(start, end):
        if day in by_date:
            filled.append(by_date[day])
            continue
        i = bisect.bisect(known, day)
        previous = by_date[known[i - 1]] if i else None
        following = by_date[known[i]] if i < len(known) else None
        match fill:
            case Fill.UP:
                candidates = [previous]
            case Fill.DOWN:
                candidates = [following]
            case Fill.MAX:
                candidates = [previous, following]
        found = [rate for rate in candidates if rate is not None]
        if found:
            source = max(found, key=lambda rate: rate.value)
            filled.append(dataclasses.replace(source, date=day))
    return filled


def _fetch(
    client: RatesClient,
    currency: str,
    start: dt.date,
    end: dt.date,
    reference_currency: str,
    granularity: Granularity,
    fill: Fill | None,
) -> list[Rate]:
    """Call the API for ``[start, end]``, widened as ``fill`` needs."""
    match granularity:
        case Granularity.DAILY:
            if fill in (Fill.UP, Fill.MAX):
                start -= FILL_WINDOW
            if fill in (Fill.DOWN, Fill.MAX):
                # The API has nothing after today: don't ask for it.
                end = max(end, min(end + FILL_WINDOW, dt.date.today()))
            return client.get_daily_time_series(
                currency, start, end, reference_currency
            )
        case Granularity.MONTHLY:
            return [
                rate
                for year, month in months_between(start, end)
                for rate in client.get_monthly_average(
                    year, month, currency, reference_currency
                )
            ]
        case Granularity.YEARLY:
            return [
                rate
                for year in range(start.year, end.year + 1)
                for rate in client.get_annual_average(
                    year, currency, reference_currency
                )
            ]


def get_rates(
    currency: str,
    start: dt.date | None = None,
    end: dt.date | None = None,
    *,
    reference_currency: str = "EUR",
    granularity: Granularity | str = Granularity.DAILY,
    fill: Fill | str | None = None,
    client: RatesClient | None = None,
) -> list[Rate]:
    """Return the rates of ``currency`` over a date range.

    Daily rates come from a single time-series request. Monthly and yearly
    averages are fetched once per month/year touched by the range.

    The API only quotes against EUR, USD and ITL. If ``reference_currency``
    is something else but ``currency`` is one of those, the pair is fetched
    the other way round and each rate is inverted (see
    :meth:`Rate.inverted`), so ``get_rates("EUR", reference_currency="KWD")``
    works.

    Args:
        currency (str): ISO code of the quoted currency, e.g. ``"USD"``.
        start (dt.date | None): First day of the range (inclusive);
            defaults to ``end``, i.e. a single day.
        end (dt.date | None): Last day (inclusive); defaults to today.
        reference_currency (str): Currency the rates are quoted against.
            ``currency`` or ``reference_currency`` must be EUR, USD or ITL.
        granularity (Granularity | str): ``daily``, ``monthly`` or ``yearly``.
        fill (Fill | str | None): Daily only. If set, every day of the range
            gets a rate, taken from the nearest days that have one (see
            :func:`fill_rates`). Up to ``FILL_WINDOW`` days outside the
            range are searched.
        client (RatesClient | None): Client to use; a default one if omitted.

    Raises:
        InvalidDateRangeError: If ``start`` is after ``end``.
        ValueError: If neither currency is EUR, USD or ITL, if
            ``granularity`` or ``fill`` is invalid, or if ``fill`` is set
            for a non-daily granularity.
        APIError: If the API can't be reached or rejects the request.

    Example:
        >>> import datetime as dt
        >>> from twocents import get_rates
        >>> get_rates(
        ...     "USD",
        ...     dt.date(2023, 1, 1),
        ...     dt.date(2023, 3, 31),
        ...     granularity="monthly",
        ... )
    """
    currency = currency.upper()
    reference_currency = reference_currency.upper()
    granularity = Granularity(granularity)
    fill = Fill(fill) if fill is not None else None
    end = end or dt.date.today()
    start = start or end
    inverted = reference_currency not in REFERENCE_CURRENCIES
    if inverted:
        if currency not in REFERENCE_CURRENCIES:
            allowed = ", ".join(REFERENCE_CURRENCIES)
            raise ValueError(
                f"currency or reference_currency must be one of {allowed}, "
                f"got {currency!r} and {reference_currency!r}"
            )
        currency, reference_currency = reference_currency, currency
    if start > end:
        raise InvalidDateRangeError(
            f"start ({start}) must not be after end ({end})"
        )
    if fill is not None and granularity is not Granularity.DAILY:
        raise ValueError("fill only applies to daily rates")

    rates = _fetch(
        client or RatesClient(),
        currency,
        start,
        end,
        reference_currency,
        granularity,
        fill,
    )
    if inverted:
        rates = [rate.inverted() for rate in rates]
    if fill is not None:
        rates = fill_rates(rates, start, end, fill)
    return rates
