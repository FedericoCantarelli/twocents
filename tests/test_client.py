import datetime as dt
from decimal import Decimal

import pytest
import requests

from tests import payloads
from tests.conftest import FakeResponse
from twocents.client import BASE_URL
from twocents.client import DEFAULT_TIMEOUT
from twocents.client import Language
from twocents.client import RatesClient
from twocents.errors import APIError
from twocents.models import ExchangeConvention
from twocents.models import Granularity


class TestRequest:
    def test_url_headers_and_timeout(self, client, fake_session):
        client.get_currencies()
        call = fake_session.calls[0]
        assert call["url"] == f"{BASE_URL}/currencies"
        assert call["params"] == {"lang": "en"}
        assert call["headers"] == {"Accept": "application/json"}
        assert call["timeout"] == DEFAULT_TIMEOUT

    def test_language_and_timeout_are_configurable(self, fake_session):
        RatesClient(Language.IT, timeout=3).get_currencies()
        assert fake_session.calls[0]["params"]["lang"] == "it"
        assert fake_session.calls[0]["timeout"] == 3

    def test_custom_session_and_base_url(self, fake_session):
        client = RatesClient(session=fake_session, base_url="http://x/api/")
        client.get_currencies()
        assert fake_session.calls[0]["url"] == "http://x/api/currencies"

    def test_http_error_becomes_api_error(self, client, fake_session):
        fake_session.on(
            "dailyTimeSeries",
            FakeResponse(
                status_code=400,
                text="WARNING! Parameter currencyIsoCode can take ...\n",
            ),
        )
        with pytest.raises(APIError) as exc_info:
            client.get_daily_time_series("USD", dt.date(2023, 1, 1))
        assert exc_info.value.status_code == 400
        assert exc_info.value.message == (
            "WARNING! Parameter currencyIsoCode can take ..."
        )
        assert str(exc_info.value).startswith("HTTP 400: WARNING!")

    def test_network_error_becomes_api_error(self, client, fake_session):
        fake_session.on("currencies", requests.ConnectionError("boom"))
        with pytest.raises(APIError, match="boom") as exc_info:
            client.get_currencies()
        assert exc_info.value.status_code is None
        assert isinstance(exc_info.value.__cause__, requests.ConnectionError)

    def test_debug_logging(self, client, fake_session, caplog):
        with caplog.at_level("DEBUG", logger="twocents"):
            client.get_currencies()
        assert "GET" in caplog.text
        assert "HTTP 200" in caplog.text


def test_get_currencies(client, fake_session):
    fake_session.on("currencies", payloads.currencies_payload())
    currencies = client.get_currencies()
    assert [c.iso_code for c in currencies] == ["USD", "XAU"]


def test_get_currencies_empty_payload(client, fake_session):
    assert client.get_currencies() == []


class TestDailyTimeSeries:
    def test_params_and_parsing(self, client, fake_session):
        fake_session.on(
            "dailyTimeSeries",
            payloads.daily_series_payload(
                [("2023-01-02", "1.2053"), ("2023-01-03", "1.2")],
                iso_code="GBP",
                convention="I",
            ),
        )
        rates = client.get_daily_time_series(
            "GBP", dt.date(2023, 1, 2), dt.date(2023, 1, 3), "USD"
        )
        assert fake_session.calls[0]["params"] == {
            "currencyIsoCode": "USD",
            "startDate": "2023-01-02",
            "endDate": "2023-01-03",
            "baseCurrencyIsoCode": "GBP",
            "lang": "en",
        }
        assert [r.date for r in rates] == [
            dt.date(2023, 1, 2),
            dt.date(2023, 1, 3),
        ]
        assert rates[0].currency == "GBP"
        assert rates[0].reference_currency == "USD"
        assert rates[0].value == Decimal("1.2053")
        assert rates[0].convention is ExchangeConvention.REFERENCE_PER_CURRENCY

    def test_end_defaults_to_today(self, client, fake_session):
        client.get_daily_time_series("USD", dt.date(2023, 1, 1))
        params = fake_session.calls[0]["params"]
        assert params["endDate"] == dt.date.today().isoformat()

    def test_empty_range(self, client, fake_session):
        fake_session.on("dailyTimeSeries", payloads.daily_series_payload([]))
        assert client.get_daily_time_series("USD", dt.date(2023, 1, 7)) == []


class TestSingleDayEndpoints:
    def test_daily_rates(self, client, fake_session):
        fake_session.on(
            "dailyRates", payloads.daily_rates_payload("2023-01-03")
        )
        (rate,) = client.get_daily_rates(dt.date(2023, 1, 3), "USD")
        assert fake_session.calls[0]["params"] == {
            "currencyIsoCode": "EUR",
            "referenceDate": "2023-01-03",
            "baseCurrencyIsoCode": "USD",
            "lang": "en",
        }
        assert rate.date == dt.date(2023, 1, 3)

    def test_monthly_average(self, client, fake_session):
        fake_session.on(
            "monthlyAverageRates", payloads.monthly_payload(2023, 1)
        )
        (rate,) = client.get_monthly_average(2023, 1, "USD")
        assert fake_session.calls[0]["params"] == {
            "currencyIsoCode": "EUR",
            "year": 2023,
            "month": 1,
            "baseCurrencyIsoCode": "USD",
            "lang": "en",
        }
        assert rate.granularity is Granularity.MONTHLY

    def test_annual_average(self, client, fake_session):
        fake_session.on("annualAverageRates", payloads.yearly_payload(2022))
        (rate,) = client.get_annual_average(2022, "USD", "USD")
        assert fake_session.calls[0]["params"] == {
            "currencyIsoCode": "USD",
            "year": 2022,
            "baseCurrencyIsoCode": "USD",
            "lang": "en",
        }
        assert rate.granularity is Granularity.YEARLY

    @pytest.mark.parametrize(
        "call",
        [
            lambda c: c.get_daily_rates(dt.date(2023, 1, 3)),
            lambda c: c.get_monthly_average(2023, 1),
            lambda c: c.get_annual_average(2023),
        ],
    )
    def test_currency_filter_is_optional(self, client, fake_session, call):
        call(client)
        assert "baseCurrencyIsoCode" not in fake_session.calls[0]["params"]
