# Package reference

Everything below is importable from `twocents` directly, unless noted otherwise.

## `get_rates`

```python
get_rates(
    currency: str,
    start: dt.date | None = None,
    end: dt.date | None = None,
    *,
    reference_currency: str = "EUR",
    granularity: Granularity | str = Granularity.DAILY,
    fill: Fill | str | None = None,
    client: RatesClient | None = None,
) -> list[Rate]
```

This is the recommended entry point and is what `tc rates convert` calls. It follows
the same rules as the CLI:

- `end` defaults to today and `start` defaults to `end`.
- Codes are upper-cased.
- If `reference_currency` isn't EUR, USD or ITL but `currency` is, the pair is
  swapped and the rates inverted.
- `fill` (`"up"`, `"down"`, `"max"`) is daily only.

Daily rates take one request. Monthly and yearly averages take one request per
month or year.

Raises:

- `InvalidDateRangeError` if `start > end`.
- `ValueError` if neither currency is EUR/USD/ITL, if `granularity` or `fill` is
  invalid, or if `fill` is used with a non-daily granularity.
- `APIError` on a network or HTTP failure.

```python
twocents.get_rates("EUR", reference_currency="KWD", fill="up")
twocents.get_rates(
    "GBP",
    dt.date(2022, 1, 1),
    dt.date(2022, 12, 31),
    reference_currency="USD",
    granularity="monthly",
)
```

## `list_currencies`

```python
list_currencies(client: RatesClient | None = None) -> list[Currency]
```

Returns every currency known to Banca d'Italia.

## Models

All models are frozen dataclasses. Each has `to_dict()`, which returns a
JSON-ready dict, and `to_row()`, which returns a flat dict for CSV.

**`Rate`**

| Attribute            | Type                 | Description                                                  |
| -------------------- | -------------------- | ------------------------------------------------------------ |
| `currency`           | `str`                | ISO code of the quoted currency.                             |
| `reference_currency` | `str`                | ISO code it is quoted against.                               |
| `value`              | `Decimal`            | The rate as published. Its direction is set by `convention`. |
| `convention`         | `ExchangeConvention` | How to read `value`.                                         |
| `granularity`        | `Granularity`        | Daily rate, or monthly/yearly average.                       |
| `date`               | `dt.date`            | The day, or the first day of the averaged period.            |

| Member                   | Description                                                                 |
| ------------------------ | --------------------------------------------------------------------------- |
| `currency_per_reference` | Units of `currency` for 1 `reference_currency`, whatever the convention.     |
| `reference_per_currency` | Units of `reference_currency` for 1 `currency`, whatever the convention.     |
| `inverted()`             | The same rate from the other side. The currencies are swapped and `value` becomes `1 / value`, rounded to `twocents.models.INVERTED_PRECISION` (6) significant digits. |
| `from_api(data, ...)`    | Builds a `Rate` from an API payload item.                                   |

Use `currency_per_reference` or `reference_per_currency` instead of `value` when you
need a number in a known direction.

**`Currency`** has `iso_code`, `name` and `countries` (a `tuple[Country, ...]`).

**`Country`** has `name`, `iso_code`, `valid_from` and `valid_to` (`dt.date | None`).

## Enums and constants

| Name                   | Values / value                                                 |
| ---------------------- | -------------------------------------------------------------- |
| `Granularity`          | `DAILY="daily"`, `MONTHLY="monthly"`, `YEARLY="yearly"`        |
| `Fill`                 | `UP="up"`, `DOWN="down"`, `MAX="max"`                          |
| `ExchangeConvention`   | `CURRENCY_PER_REFERENCE="C"`, `REFERENCE_PER_CURRENCY="I"`     |
| `Language`             | `IT="it"`, `EN="en"` (language of currency and country names)  |
| `REFERENCE_CURRENCIES` | `("EUR", "USD", "ITL")`                                        |

`Granularity`, `Fill` and `ExchangeConvention` are `StrEnum`s, so plain strings work
wherever they are expected.

## Helpers in `twocents.service`

These are importable from `twocents.service`, not from `twocents`.

| Name                                  | Description                                                                 |
| ------------------------------------- | --------------------------------------------------------------------------- |
| `fill_rates(rates, start, end, fill)` | One rate per day of `[start, end]`, with gaps filled. Rates outside the range only serve as neighbours. |
| `days_between(start, end)`            | Yields every day of `[start, end]`.                                         |
| `months_between(start, end)`          | Yields every `(year, month)` touched by `[start, end]`.                     |
| `FILL_WINDOW`                         | How far outside the range filling looks (`timedelta(days=14)`).             |

## `RatesClient`

This is the low-level client. Each method calls exactly one endpoint and does no
validation, date-range logic, swapping or filling.

```python
RatesClient(
    language: Language = Language.EN,
    *,
    session: requests.Session | None = None,
    timeout: float = 30.0,
    base_url: str = BASE_URL,
)
```

| Method                                                                       | Endpoint              |
| ---------------------------------------------------------------------------- | --------------------- |
| `get_currencies() -> list[Currency]`                                         | `currencies`          |
| `get_daily_rates(reference_date, currency=None, reference_currency="EUR")`   | `dailyRates`          |
| `get_daily_time_series(currency, start, end=None, reference_currency="EUR")` | `dailyTimeSeries`     |
| `get_monthly_average(year, month, currency=None, reference_currency="EUR")`  | `monthlyAverageRates` |
| `get_annual_average(year, currency=None, reference_currency="EUR")`          | `annualAverageRates`  |

Rate methods return `list[Rate]`. If you leave out `currency`, you get every currency
for that day, month or year. Here `reference_currency` must be EUR, USD or ITL.

## Exporters

| Class          | Format                                                         |
| -------------- | -------------------------------------------------------------- |
| `JsonExporter` | Indented JSON array of `to_dict()`                             |
| `CsvExporter`  | CSV of `to_row()` with a header. An empty list writes nothing. |

Both implement the `Exporter` ABC:

- `dump(records, stream)` writes to any text stream, e.g. `sys.stdout`.
- `export(records, path)` writes to a file and overwrites it. The parent directory
  must exist.

`twocents.exporters.EXPORTERS` maps format names to classes.

## Errors

```
TwocentsError
├── APIError                 # .status_code (int | None), .message
└── InvalidDateRangeError    # also a ValueError
```

`APIError.status_code` is `None` when no response was received, for example on a
timeout.

## Logging

Requests are logged at `DEBUG` level to the `twocents` logger, which has a
`NullHandler` by default. To see them, run
`logging.basicConfig(level="DEBUG")` or
`logging.getLogger("twocents").setLevel("DEBUG")`.
