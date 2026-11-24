import csv
import datetime as dt
import io
import json
from decimal import Decimal

import pytest

from twocents.exporters import EXPORTERS
from twocents.exporters import CsvExporter
from twocents.exporters import Exporter
from twocents.exporters import JsonExporter
from twocents.models import Country
from twocents.models import Currency
from twocents.models import ExchangeConvention
from twocents.models import Granularity
from twocents.models import Rate


@pytest.fixture
def rates() -> list[Rate]:
    return [
        Rate(
            currency="USD",
            reference_currency="EUR",
            value=Decimal(value),
            convention=ExchangeConvention.CURRENCY_PER_REFERENCE,
            granularity=Granularity.DAILY,
            date=dt.date(2023, 1, day),
        )
        for day, value in [(2, "1.0683"), (3, "1.0545")]
    ]


@pytest.fixture
def currencies() -> list[Currency]:
    return [
        Currency(
            "USD",
            "Dollar, U.S.",
            (Country("UNITED STATES", "US", None, None),),
        )
    ]


def test_base_exporter_is_abstract():
    with pytest.raises(TypeError):
        Exporter()  # ty: ignore[abstract-class-instantiation]


def test_registry():
    assert {"json": JsonExporter, "csv": CsvExporter} == EXPORTERS


class TestJsonExporter:
    def test_dump(self, rates):
        out = io.StringIO()
        JsonExporter().dump(rates, out)
        assert json.loads(out.getvalue()) == [r.to_dict() for r in rates]
        assert out.getvalue().endswith("]\n")

    def test_nested_records(self, currencies):
        out = io.StringIO()
        JsonExporter().dump(currencies, out)
        assert json.loads(out.getvalue())[0]["countries"][0]["name"] == (
            "UNITED STATES"
        )

    def test_empty(self):
        out = io.StringIO()
        JsonExporter().dump([], out)
        assert json.loads(out.getvalue()) == []


class TestCsvExporter:
    def test_dump(self, rates):
        out = io.StringIO()
        CsvExporter().dump(rates, out)
        lines = out.getvalue().splitlines()
        assert lines[0] == (
            "currency,reference_currency,date,granularity,value,convention"
        )
        assert lines[1] == "USD,EUR,2023-01-02,daily,1.0683,C"
        assert "\r" not in out.getvalue()

    def test_uses_flat_rows_and_quotes_commas(self, currencies):
        out = io.StringIO()
        CsvExporter().dump(currencies, out)
        out.seek(0)
        assert list(csv.DictReader(out)) == [
            {
                "iso_code": "USD",
                "name": "Dollar, U.S.",
                "countries": "UNITED STATES",
            }
        ]

    def test_empty_writes_nothing(self):
        out = io.StringIO()
        CsvExporter().dump([], out)
        assert out.getvalue() == ""


class TestExportToFile:
    @pytest.mark.parametrize("exporter", [JsonExporter(), CsvExporter()])
    def test_writes_file(self, tmp_path, rates, exporter):
        target = tmp_path / f"out.{exporter.name}"
        exporter.export(rates, target)
        expected = io.StringIO()
        exporter.dump(rates, expected)
        assert target.read_text() == expected.getvalue()

    def test_accepts_str_path(self, tmp_path, rates):
        JsonExporter().export(rates, str(tmp_path / "out.json"))
        assert (tmp_path / "out.json").exists()

    def test_overwrites(self, tmp_path, rates):
        target = tmp_path / "out.json"
        target.write_text("old")
        JsonExporter().export(rates, target)
        assert json.loads(target.read_text())

    def test_missing_directory(self, tmp_path, rates):
        with pytest.raises(FileNotFoundError):
            JsonExporter().export(rates, tmp_path / "missing" / "out.json")
