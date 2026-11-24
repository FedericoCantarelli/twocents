import datetime as dt
from decimal import Decimal

import pytest

from tests import payloads
from twocents.errors import InvalidDateRangeError
from twocents.models import ExchangeConvention
from twocents.models import Fill
from twocents.models import Granularity
from twocents.models import Rate
from twocents.service import FILL_WINDOW
from twocents.service import days_between
from twocents.service import fill_rates
from twocents.service import get_rates
from twocents.service import list_currencies
from twocents.service import months_between


D = dt.date


class TestMonthsBetween:
    def test_same_month(self):
        assert list(months_between(D(2023, 1, 5), D(2023, 1, 20))) == [
            (2023, 1)
        ]

    def test_crosses_year_boundary(self):
        assert list(months_between(D(2022, 11, 15), D(2023, 2, 1))) == [
            (2022, 11),
            (2022, 12),
            (2023, 1),
            (2023, 2),
        ]

    def test_multiple_years(self):
        months = list(months_between(D(2021, 12, 1), D(2023, 1, 1)))
        assert len(months) == 14
        assert months[0] == (2021, 12)
        assert months[-1] == (2023, 1)

    def test_empty_when_reversed(self):
        assert list(months_between(D(2023, 2, 1), D(2023, 1, 1))) == []


def test_list_currencies(client, fake_session):
    fake_session.on("currencies", payloads.currencies_payload())
    assert len(list_currencies(client)) == 2


def test_list_currencies_default_client(fake_session):
    fake_session.on("currencies", payloads.currencies_payload())
    assert len(list_currencies()) == 2


class TestGetRates:
    def test_daily_is_single_time_series_call(self, client, fake_session):
        fake_session.on(
            "dailyTimeSeries",
            payloads.daily_series_payload([("2023-01-02", "1.0683")]),
        )
        rates = get_rates("USD", D(2023, 1, 1), D(2023, 1, 31), client=client)
        assert fake_session.endpoints == ["dailyTimeSeries"]
        assert len(rates) == 1

    def test_monthly_calls_once_per_month(self, client, fake_session):
        fake_session.on(
            "monthlyAverageRates",
            lambda p: payloads.monthly_payload(p["year"], p["month"]),
        )
        rates = get_rates(
            "USD",
            D(2022, 12, 15),
            D(2023, 2, 1),
            granularity=Granularity.MONTHLY,
            client=client,
        )
        assert fake_session.endpoints == ["monthlyAverageRates"] * 3
        assert [r.date for r in rates] == [
            D(2022, 12, 1),
            D(2023, 1, 1),
            D(2023, 2, 1),
        ]

    def test_yearly_calls_once_per_year(self, client, fake_session):
        fake_session.on(
            "annualAverageRates", lambda p: payloads.yearly_payload(p["year"])
        )
        rates = get_rates(
            "USD",
            D(2020, 6, 1),
            D(2022, 1, 1),
            granularity="yearly",
            client=client,
        )
        assert fake_session.endpoints == ["annualAverageRates"] * 3
        assert [r.date.year for r in rates] == [2020, 2021, 2022]

    def test_months_without_data_are_skipped(self, client, fake_session):
        fake_session.on(
            "monthlyAverageRates",
            lambda p: (
                payloads.monthly_payload(2023, 1)
                if p["month"] == 1
                else payloads.EMPTY
            ),
        )
        rates = get_rates(
            "USD",
            D(2023, 1, 1),
            D(2023, 3, 1),
            granularity="monthly",
            client=client,
        )
        assert len(rates) == 1

    def test_codes_are_uppercased(self, client, fake_session):
        get_rates(
            "usd",
            D(2023, 1, 1),
            D(2023, 1, 2),
            reference_currency="usd",
            client=client,
        )
        params = fake_session.calls[0]["params"]
        assert params["baseCurrencyIsoCode"] == "USD"
        assert params["currencyIsoCode"] == "USD"

    def test_end_defaults_to_today(self, client, fake_session):
        get_rates("USD", D(2023, 1, 1), client=client)
        params = fake_session.calls[0]["params"]
        assert params["endDate"] == dt.date.today().isoformat()

    def test_start_after_end(self, client, fake_session):
        with pytest.raises(InvalidDateRangeError):
            get_rates("USD", D(2023, 2, 1), D(2023, 1, 1), client=client)
        assert fake_session.calls == []

    def test_invalid_date_range_is_a_value_error(self, client):
        with pytest.raises(ValueError):
            get_rates("USD", D(2023, 2, 1), D(2023, 1, 1), client=client)

    def test_invalid_reference_currency(self, client, fake_session):
        with pytest.raises(ValueError, match="EUR, USD, ITL"):
            get_rates(
                "CHF", D(2023, 1, 1), reference_currency="GBP", client=client
            )
        assert fake_session.calls == []

    def test_unsupported_reference_is_swapped(self, client, fake_session):
        fake_session.on(
            "dailyTimeSeries",
            payloads.daily_series_payload(
                [("2023-01-02", "0.25")], iso_code="KWD"
            ),
        )
        [rate] = get_rates(
            "EUR", D(2023, 1, 2), reference_currency="kwd", client=client
        )
        params = fake_session.calls[0]["params"]
        assert params["baseCurrencyIsoCode"] == "KWD"
        assert params["currencyIsoCode"] == "EUR"
        assert (rate.currency, rate.reference_currency) == ("EUR", "KWD")
        assert rate.value == Decimal(4)

    def test_swapped_monthly(self, client, fake_session):
        fake_session.on(
            "monthlyAverageRates",
            lambda p: payloads.monthly_payload(
                p["year"], p["month"], value="0.5", iso_code="KWD"
            ),
        )
        rates = get_rates(
            "EUR",
            D(2023, 1, 1),
            D(2023, 2, 1),
            reference_currency="KWD",
            granularity="monthly",
            client=client,
        )
        assert [r.value for r in rates] == [Decimal(2), Decimal(2)]

    def test_fillmax_compares_inverted_values(self, client, fake_session):
        # Inverted: 2023-01-02 -> 4, 2023-01-04 -> 2. Max on the 3rd is 4.
        fake_session.on(
            "dailyTimeSeries",
            payloads.daily_series_payload(
                [("2023-01-02", "0.25"), ("2023-01-04", "0.5")],
                iso_code="KWD",
            ),
        )
        rates = get_rates(
            "EUR",
            D(2023, 1, 3),
            D(2023, 1, 3),
            reference_currency="KWD",
            fill="max",
            client=client,
        )
        assert [r.value for r in rates] == [Decimal(4)]

    def test_invalid_granularity(self, client):
        with pytest.raises(ValueError):
            get_rates("USD", D(2023, 1, 1), granularity="weekly", client=client)

    def test_start_defaults_to_end(self, client, fake_session):
        get_rates("USD", end=D(2023, 1, 5), client=client)
        params = fake_session.calls[0]["params"]
        assert params["startDate"] == params["endDate"] == "2023-01-05"

    def test_no_dates_means_today(self, client, fake_session):
        get_rates("USD", client=client)
        params = fake_session.calls[0]["params"]
        today = dt.date.today().isoformat()
        assert params["startDate"] == params["endDate"] == today

    def test_fill_up_looks_back(self, client, fake_session):
        fake_session.on(
            "dailyTimeSeries",
            payloads.daily_series_payload([("2022-12-30", "1.0666")]),
        )
        rates = get_rates(
            "USD", D(2023, 1, 1), D(2023, 1, 2), fill="up", client=client
        )
        params = fake_session.calls[0]["params"]
        assert params["startDate"] == (D(2023, 1, 1) - FILL_WINDOW).isoformat()
        assert params["endDate"] == "2023-01-02"
        assert [(r.date, r.value) for r in rates] == [
            (D(2023, 1, 1), Decimal("1.0666")),
            (D(2023, 1, 2), Decimal("1.0666")),
        ]

    def test_fill_down_looks_ahead(self, client, fake_session):
        get_rates(
            "USD", D(2023, 1, 1), D(2023, 1, 2), fill="down", client=client
        )
        params = fake_session.calls[0]["params"]
        assert params["startDate"] == "2023-01-01"
        assert params["endDate"] == (D(2023, 1, 2) + FILL_WINDOW).isoformat()

    def test_fill_down_never_asks_past_today(self, client, fake_session):
        get_rates("USD", fill=Fill.DOWN, client=client)
        params = fake_session.calls[0]["params"]
        assert params["endDate"] == dt.date.today().isoformat()

    def test_fill_requires_daily(self, client, fake_session):
        with pytest.raises(ValueError, match="daily"):
            get_rates(
                "USD",
                D(2023, 1, 1),
                granularity="monthly",
                fill="up",
                client=client,
            )
        assert fake_session.calls == []

    def test_invalid_fill(self, client):
        with pytest.raises(ValueError):
            get_rates("USD", D(2023, 1, 1), fill="sideways", client=client)


def _rate(day: dt.date, value: str) -> Rate:
    return Rate(
        currency="USD",
        reference_currency="EUR",
        value=Decimal(value),
        convention=ExchangeConvention.CURRENCY_PER_REFERENCE,
        granularity=Granularity.DAILY,
        date=day,
    )


def test_days_between():
    assert list(days_between(D(2023, 1, 30), D(2023, 2, 1))) == [
        D(2023, 1, 30),
        D(2023, 1, 31),
        D(2023, 2, 1),
    ]


class TestFillRates:
    # Rates on the 2nd (low) and the 5th (high); gaps on 1st, 3rd, 4th, 6th.
    RATES = (_rate(D(2023, 1, 2), "1.0"), _rate(D(2023, 1, 5), "2.0"))

    def _values(self, fill):
        rates = fill_rates(self.RATES, D(2023, 1, 1), D(2023, 1, 6), fill)
        return {r.date.day: str(r.value) for r in rates}

    def test_up(self):
        assert self._values(Fill.UP) == {
            2: "1.0", 3: "1.0", 4: "1.0", 5: "2.0", 6: "2.0"
        }  # fmt: skip

    def test_down(self):
        assert self._values("down") == {
            1: "1.0", 2: "1.0", 3: "2.0", 4: "2.0", 5: "2.0"
        }  # fmt: skip

    def test_max(self):
        assert self._values("max") == {
            1: "1.0", 2: "1.0", 3: "2.0", 4: "2.0", 5: "2.0", 6: "2.0"
        }  # fmt: skip

    def test_filled_rates_keep_everything_but_the_date(self):
        filled = fill_rates(self.RATES, D(2023, 1, 3), D(2023, 1, 3), "up")
        assert filled == [_rate(D(2023, 1, 3), "1.0")]

    def test_rates_outside_the_range_are_dropped(self):
        filled = fill_rates(self.RATES, D(2023, 1, 3), D(2023, 1, 4), "up")
        assert [r.date for r in filled] == [D(2023, 1, 3), D(2023, 1, 4)]

    def test_no_rates(self):
        assert fill_rates([], D(2023, 1, 1), D(2023, 1, 3), "max") == []
