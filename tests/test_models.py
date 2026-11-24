import datetime as dt
from decimal import Decimal

import pytest

from tests import payloads
from twocents.models import Country
from twocents.models import Currency
from twocents.models import ExchangeConvention
from twocents.models import Granularity
from twocents.models import Rate


def make_rate(value="2", convention="C") -> Rate:
    return Rate(
        currency="USD",
        reference_currency="EUR",
        value=Decimal(value),
        convention=ExchangeConvention(convention),
        granularity=Granularity.DAILY,
        date=dt.date(2023, 1, 2),
    )


class TestRateFromApi:
    def test_daily_series_row_uses_results_info_defaults(self):
        payload = payloads.daily_series_payload(
            [("2023-01-02", "1.0683")], iso_code="USD", convention="C"
        )
        rate = Rate.from_api(
            payload["rates"][0],
            reference_currency="EUR",
            granularity=Granularity.DAILY,
            defaults=payload["resultsInfo"],
        )
        assert rate == Rate(
            currency="USD",
            reference_currency="EUR",
            value=Decimal("1.0683"),
            convention=ExchangeConvention.CURRENCY_PER_REFERENCE,
            granularity=Granularity.DAILY,
            date=dt.date(2023, 1, 2),
        )

    def test_row_fields_win_over_defaults(self):
        row = payloads.daily_rates_payload("2023-01-03", iso_code="GBP")
        rate = Rate.from_api(
            row["rates"][0],
            reference_currency="EUR",
            granularity=Granularity.DAILY,
            defaults={"isoCode": "USD"},
        )
        assert rate.currency == "GBP"

    def test_monthly_date_is_first_of_month(self):
        row = payloads.monthly_payload(2023, 7)["rates"][0]
        rate = Rate.from_api(
            row, reference_currency="EUR", granularity=Granularity.MONTHLY
        )
        assert rate.date == dt.date(2023, 7, 1)
        assert rate.granularity is Granularity.MONTHLY

    def test_yearly_date_is_first_of_year(self):
        row = payloads.yearly_payload(2022)["rates"][0]
        rate = Rate.from_api(
            row, reference_currency="EUR", granularity=Granularity.YEARLY
        )
        assert rate.date == dt.date(2022, 1, 1)

    def test_value_is_exact_decimal(self):
        row = payloads.yearly_payload(2022, value="0.1")["rates"][0]
        rate = Rate.from_api(
            row, reference_currency="EUR", granularity=Granularity.YEARLY
        )
        assert rate.value == Decimal("0.1")

    def test_unknown_convention_raises(self):
        row = payloads.yearly_payload(2022, convention="Z")["rates"][0]
        with pytest.raises(ValueError):
            Rate.from_api(
                row, reference_currency="EUR", granularity=Granularity.YEARLY
            )


class TestRateConvention:
    def test_currency_per_reference_convention(self):
        rate = make_rate("2", "C")
        assert rate.currency_per_reference == Decimal("2")
        assert rate.reference_per_currency == Decimal("0.5")

    def test_reference_per_currency_convention(self):
        rate = make_rate("4", "I")
        assert rate.reference_per_currency == Decimal("4")
        assert rate.currency_per_reference == Decimal("0.25")


def test_rate_to_dict_is_json_friendly():
    assert make_rate("1.0683").to_dict() == {
        "currency": "USD",
        "reference_currency": "EUR",
        "date": "2023-01-02",
        "granularity": "daily",
        "value": "1.0683",
        "convention": "C",
    }


def test_rate_is_immutable():
    with pytest.raises(AttributeError):
        make_rate().value = Decimal(1)  # ty: ignore[invalid-assignment]


class TestCurrency:
    def test_from_api(self):
        raw = payloads.currencies_payload()["currencies"][0]
        currency = Currency.from_api(raw)
        assert currency.iso_code == "USD"
        assert currency.name == "U.S. Dollar"
        assert currency.countries == (
            Country("UNITED STATES", "US", dt.date(1918, 1, 1), None),
            Country("ECUADOR", None, None, None),
        )

    def test_no_countries(self):
        raw = payloads.currencies_payload()["currencies"][1]
        assert Currency.from_api(raw).countries == ()

    def test_null_countries(self):
        currency = Currency.from_api(
            {"isoCode": "X", "name": "X", "countries": None}
        )
        assert currency.countries == ()

    def test_to_dict_nests_countries(self):
        raw = payloads.currencies_payload()["currencies"][0]
        data = Currency.from_api(raw).to_dict()
        assert data["countries"][0] == {
            "name": "UNITED STATES",
            "iso_code": "US",
            "valid_from": "1918-01-01",
            "valid_to": None,
        }

    def test_to_row_flattens_countries(self):
        raw = payloads.currencies_payload()["currencies"][0]
        assert Currency.from_api(raw).to_row() == {
            "iso_code": "USD",
            "name": "U.S. Dollar",
            "countries": "UNITED STATES; ECUADOR",
        }


def test_inverted():
    rate = Rate(
        currency="KWD",
        reference_currency="EUR",
        value=Decimal("0.25"),
        convention=ExchangeConvention.CURRENCY_PER_REFERENCE,
        granularity=Granularity.DAILY,
        date=dt.date(2023, 1, 2),
    )
    inv = rate.inverted()
    assert (inv.currency, inv.reference_currency) == ("EUR", "KWD")
    assert inv.value == Decimal(4)
    assert inv.convention is rate.convention
    assert inv.date == rate.date
    # Same economic meaning, seen from the other side.
    assert inv.reference_per_currency == rate.currency_per_reference
    assert inv.inverted() == rate


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0.3609", "2.77085"),
        ("0.0055", "181.818"),
        ("150.25", "0.00665557"),
    ],
)
def test_inverted_is_rounded(value, expected):
    rate = make_rate(value)
    assert str(rate.inverted().value) == expected
