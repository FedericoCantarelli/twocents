import datetime as dt
import json

import pytest
import requests

from tests import payloads
from tests.conftest import FakeResponse
from twocents import __version__
from twocents.cli import main

DAILY = payloads.daily_series_payload(
    [("2023-01-02", "1.0683"), ("2023-01-03", "1.0545")]
)


def convert(runner, *args: str):
    return runner.invoke(
        main, ["rates", "convert", "--from", "USD", "--from-date", *args]
    )


def test_help(runner):
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "rates" in result.output
    assert "version" in result.output


def test_version(runner):
    result = runner.invoke(main, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.output


class TestList:
    def test_json_to_stdout(self, runner, fake_session):
        fake_session.on("currencies", payloads.currencies_payload())
        result = runner.invoke(main, ["rates", "list"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.stdout)
        assert [c["iso_code"] for c in data] == ["USD", "XAU"]

    def test_csv_to_stdout(self, runner, fake_session):
        fake_session.on("currencies", payloads.currencies_payload())
        result = runner.invoke(main, ["rates", "list", "--format", "csv"])
        assert result.exit_code == 0, result.output
        assert result.stdout.splitlines() == [
            "iso_code,name,countries",
            "USD,U.S. Dollar,UNITED STATES; ECUADOR",
            'XAU,"Gold, Ounce",',
        ]

    def test_to_file(self, runner, fake_session, tmp_path):
        fake_session.on("currencies", payloads.currencies_payload())
        target = tmp_path / "currencies.json"
        result = runner.invoke(main, ["rates", "list", "--file", str(target)])
        assert result.exit_code == 0, result.output
        assert result.stdout == ""
        assert len(json.loads(target.read_text())) == 2

    def test_invalid_format(self, runner, fake_session):
        result = runner.invoke(main, ["rates", "list", "--format", "xml"])
        assert result.exit_code == 2
        assert fake_session.calls == []


class TestConvert:
    def test_default_is_daily_against_eur(self, runner, fake_session):
        fake_session.on("dailyTimeSeries", DAILY)
        result = convert(runner, "2023-01-01", "--to-date", "2023-01-31")
        assert result.exit_code == 0, result.output
        assert fake_session.endpoints == ["dailyTimeSeries"]
        params = fake_session.calls[0]["params"]
        assert params["currencyIsoCode"] == "EUR"
        assert params["startDate"] == "2023-01-01"
        assert params["endDate"] == "2023-01-31"
        data = json.loads(result.stdout)
        assert [r["value"] for r in data] == ["1.0683", "1.0545"]

    def test_explicit_daily(self, runner, fake_session):
        result = convert(runner, "2023-01-01", "--daily")
        assert result.exit_code == 0, result.output
        assert fake_session.endpoints == ["dailyTimeSeries"]

    def test_monthly_only_calls_monthly(self, runner, fake_session):
        fake_session.on(
            "monthlyAverageRates",
            lambda p: payloads.monthly_payload(p["year"], p["month"]),
        )
        result = convert(runner, "2022-12-15", "--to-date", "2023-01-10", "--monthly")
        assert result.exit_code == 0, result.output
        assert fake_session.endpoints == ["monthlyAverageRates"] * 2
        dates = [r["date"] for r in json.loads(result.stdout)]
        assert dates == ["2022-12-01", "2023-01-01"]

    def test_yearly(self, runner, fake_session):
        fake_session.on(
            "annualAverageRates", lambda p: payloads.yearly_payload(p["year"])
        )
        result = convert(runner, "2021-01-01", "--to-date", "2022-06-01", "--yearly")
        assert result.exit_code == 0, result.output
        assert fake_session.endpoints == ["annualAverageRates"] * 2

    def test_reference_currency_is_case_insensitive(self, runner, fake_session):
        result = convert(runner, "2023-01-01", "--to", "usd")
        assert result.exit_code == 0, result.output
        assert fake_session.calls[0]["params"]["currencyIsoCode"] == "USD"

    def test_unsupported_reference_currency(self, runner, fake_session):
        result = runner.invoke(
            main, ["rates", "convert", "--from", "GBP", "--to", "chf"]
        )
        assert result.exit_code == 2
        assert "only quotes against EUR, USD, ITL" in result.output
        assert "got GBP and CHF" in result.output
        assert fake_session.calls == []

    def test_unsupported_to_swaps_and_inverts(self, runner, fake_session):
        fake_session.on(
            "dailyTimeSeries",
            payloads.daily_series_payload([("2023-01-02", "0.25")], iso_code="KWD"),
        )
        result = runner.invoke(
            main,
            [
                "rates", "convert", "--from", "eur", "--to", "KWD",
                "--from-date", "2023-01-02",
            ],
        )  # fmt: skip
        assert result.exit_code == 0, result.output
        params = fake_session.calls[0]["params"]
        assert params["baseCurrencyIsoCode"] == "KWD"
        assert params["currencyIsoCode"] == "EUR"
        [rate] = json.loads(result.stdout)
        assert rate["currency"] == "EUR"
        assert rate["reference_currency"] == "KWD"
        assert rate["value"] == "4"

    def test_csv_to_file(self, runner, fake_session, tmp_path):
        fake_session.on("dailyTimeSeries", DAILY)
        target = tmp_path / "rates.csv"
        result = convert(
            runner,
            "2023-01-01",
            "--format", "csv", "--file", str(target),
        )  # fmt: skip
        assert result.exit_code == 0, result.output
        assert target.read_text().splitlines() == [
            "currency,reference_currency,date,granularity,value,convention",
            "USD,EUR,2023-01-02,daily,1.0683,C",
            "USD,EUR,2023-01-03,daily,1.0545,C",
        ]

    @pytest.mark.parametrize(
        "args",
        [
            ["01/01/2023"],
            ["2023-01-01", "--to-date", "nope"],
            ["2023-02-30"],
        ],
    )
    def test_invalid_dates(self, runner, fake_session, args):
        result = convert(runner, *args)
        assert result.exit_code == 2
        assert "YYYY-MM-DD" in result.output or "%Y-%m-%d" in result.output
        assert fake_session.calls == []

    def test_start_after_end(self, runner, fake_session):
        result = convert(runner, "2023-05-01", "--to-date", "2023-01-01")
        assert result.exit_code == 2
        assert "must not be after" in result.output
        assert fake_session.calls == []

    def test_currency_is_required(self, runner, fake_session):
        result = runner.invoke(main, ["rates", "convert", "--from-date", "2023-01-01"])
        assert result.exit_code == 2
        assert "Missing option" in result.output

    def test_no_dates_means_today(self, runner, fake_session):
        result = runner.invoke(main, ["rates", "convert", "--from", "USD"])
        assert result.exit_code == 0, result.output
        params = fake_session.calls[0]["params"]
        today = dt.date.today().isoformat()
        assert params["startDate"] == params["endDate"] == today

    def test_only_to_date_is_a_single_day(self, runner, fake_session):
        result = runner.invoke(
            main,
            ["rates", "convert", "--from", "USD", "--to-date", "2023-01-05"],
        )
        assert result.exit_code == 0, result.output
        params = fake_session.calls[0]["params"]
        assert params["startDate"] == params["endDate"] == "2023-01-05"

    @pytest.mark.parametrize(
        ("flag", "expected"),
        [
            ("--fillup", ["1.0683", "1.0683", "1.0683", "1.0545"]),
            ("--filldown", ["1.0545", "1.0545", "1.0545", "1.0545"]),
            ("--fillmax", ["1.0683", "1.0683", "1.0683", "1.0545"]),
        ],
    )
    def test_fill(self, runner, fake_session, flag, expected):
        # Rates for Fri 2022-12-30 and Tue 2023-01-03 only.
        fake_session.on(
            "dailyTimeSeries",
            payloads.daily_series_payload(
                [("2022-12-30", "1.0683"), ("2023-01-03", "1.0545")]
            ),
        )
        result = convert(runner, "2022-12-31", "--to-date", "2023-01-03", flag)
        assert result.exit_code == 0, result.output
        data = json.loads(result.stdout)
        assert [r["date"] for r in data] == [
            "2022-12-31",
            "2023-01-01",
            "2023-01-02",
            "2023-01-03",
        ]
        assert [r["value"] for r in data] == expected

    def test_fill_flags_are_exclusive(self, runner, fake_session):
        result = convert(runner, "2023-01-01", "--fillup", "--filldown")
        assert result.exit_code == 0, result.output
        params = fake_session.calls[0]["params"]
        # The last flag wins (--filldown): no look-back before the range.
        assert params["startDate"] == "2023-01-01"

    @pytest.mark.parametrize("granularity", ["--monthly", "--yearly"])
    def test_fill_requires_daily(self, runner, fake_session, granularity):
        result = convert(runner, "2023-01-01", granularity, "--fillup")
        assert result.exit_code == 2
        assert "only apply to --daily" in result.output
        assert fake_session.calls == []

    def test_api_error_is_clean(self, runner, fake_session):
        fake_session.on("dailyTimeSeries", FakeResponse(status_code=500, text="Oops"))
        result = convert(runner, "2023-01-01")
        assert result.exit_code == 1
        assert "Error: HTTP 500: Oops" in result.output
        assert "Traceback" not in result.output

    def test_network_error_is_clean(self, runner, fake_session):
        fake_session.on("dailyTimeSeries", requests.Timeout("timed out"))
        result = convert(runner, "2023-01-01")
        assert result.exit_code == 1
        assert "timed out" in result.output

    def test_missing_output_directory(self, runner, fake_session, tmp_path):
        fake_session.on("dailyTimeSeries", DAILY)
        result = convert(
            runner, "2023-01-01", "--file", str(tmp_path / "no" / "x.json")
        )
        assert result.exit_code == 1
        assert "Could not open file" in result.output

    def test_verbose_logs_to_stderr_only(self, runner, fake_session):
        fake_session.on("dailyTimeSeries", DAILY)
        result = convert(runner, "2023-01-01", "--verbose")
        assert result.exit_code == 0, result.output
        assert "GET " in result.stderr
        assert "GET " not in result.stdout
        json.loads(result.stdout)  # stdout stays valid JSON

    def test_verbose_does_not_leak_between_runs(self, runner, fake_session):
        convert(runner, "2023-01-01", "--verbose")
        result = convert(runner, "2023-01-01")
        assert result.stderr == ""
