# Two Cents

Currency exchange rates from [Banca d'Italia](https://tassidicambio.bancaditalia.it), no API key is required.

Both as a **Python module** and as `tc`. 

- [Installation](#installation)
- [Quick start](#quick-start)
- [CLI reference](#cli-reference)
- [Package reference](#package-reference)
- [Development](#development)

## Installation

```bash
git clone https://github.com/FedericoCantarelli/twocents.git
cd twocents
```

| You want…          | Install with                          |
| ------------------ | ------------------------------------- |
| The library only   | `uv add ./twocents` / `pip install .` |
| The `tc` command   | `uv tool install '.[cli]'`            |
| Both, in a project | `uv add './twocents[cli]'`            |

Running `tc` without the `cli` extra prints a message explaining how to install it.

## Quick start

```bash
tc rates convert --from USD                       # today's USD/EUR rate
tc rates convert --from EUR --to KWD --fillup     # today's EUR/KWD, or the last published
tc rates convert --from USD --from-date 2024-01-01 --to-date 2024-01-31 --format csv
```

```python
import datetime as dt

import twocents

rates = twocents.get_rates("USD", dt.date(2023, 1, 1), dt.date(2023, 1, 31))
for rate in rates:
    print(rate.date, rate.currency_per_reference)

twocents.CsvExporter().export(rates, "rates.csv")
```

---

## CLI reference

```
tc [-h] COMMAND
├── version
└── rates
    ├── list
    └── convert
```

The output is JSON on stdout unless you pass `--format csv` or `--file PATH`.


### `tc version`

Prints the installed version.

### `tc rates list`

Lists every currency known to Banca d'Italia, with the countries that use it.

| Option            | Default | Description                         |
| ----------------- | ------- | ----------------------------------- |
| `--format FORMAT` | `json`  | `json` or `csv` (case-insensitive). |
| `--file PATH`     | stdout  | Write the output to this file.      |
| `--verbose`       | off     | Log the requests made to stderr.    |

In CSV output, countries are joined with `; `.

### `tc rates convert`

Gets the exchange rates of a currency over a date range.

```bash
tc rates convert --from USD --to EUR --from-date 2023-01-01 --to-date 2023-01-31
```

| Option                   | Default     | Description                                                     |
| ------------------------ | ----------- | --------------------------------------------------------------- |
| `--from CODE`            | required    | ISO code of the currency to get rates for (e.g. `USD`).         |
| `--to CODE`              | `EUR`       | Currency the rates are quoted against. See [Currency pairs](#currency-pairs). |
| `--from-date YYYY-MM-DD` | `--to-date` | First day of the range (inclusive).                             |
| `--to-date YYYY-MM-DD`   | today       | Last day of the range (inclusive).                              |
| `--daily`                | on          | Daily rates.                                                    |
| `--monthly`              | off         | Monthly averages, one request per month in the range.           |
| `--yearly`               | off         | Yearly averages, one request per year in the range.             |
| `--fillup`               | off         | Daily only: fill a day without a rate with the previous rate.   |
| `--filldown`             | off         | Daily only: fill a day without a rate with the next rate.       |
| `--fillmax`              | off         | Daily only: fill with the larger of the previous and next rate. |
| `--format FORMAT`        | `json`      | `json` or `csv`.                                                |
| `--file PATH`            | stdout      | Write the output to this file.                                  |
| `--verbose`              | off         | Log the requests made to stderr.                                |

Currency codes are case-insensitive. `--daily`, `--monthly` and `--yearly` are
mutually exclusive, and so are `--fillup`, `--filldown` and `--fillmax`. In both
groups the last flag given wins.

#### Dates

| Given              | Range                       |
| ------------------ | --------------------------- |
| neither            | today only                  |
| `--from-date` only | `--from-date` → today       |
| `--to-date` only   | that single day             |
| both               | `--from-date` → `--to-date` |

With `--monthly` and `--yearly`, the range covers every month or year it touches.

#### Currency pairs

Banca d'Italia only quotes against **EUR, USD and ITL**, so `--from` or `--to` must
be one of them.

- If `--to` is one of them, you get the published rate.
- If it isn't (e.g. `--from EUR --to KWD`), the pair is fetched the other way round.
  Every rate is then inverted (`1 / rate`, rounded to 6 significant digits), so the
  output reads `currency=EUR`, `reference_currency=KWD`.
- If neither is (e.g. `--from GBP --to CHF`), you get a usage error.

#### Filling missing days

By default you only get the days Banca d'Italia published a rate for, so weekends
and holidays are missing. A fill flag returns one row per calendar day instead. A
day without a rate gets a copy of a neighbouring rate, with that day's date:

| Flag         | A missing day takes…                        |
| ------------ | ------------------------------------------- |
| `--fillup`   | the last earlier rate                       |
| `--filldown` | the first later rate                        |
| `--fillmax`  | the larger of the two (or whichever exists) |

To find neighbours for the first and last days, the search goes up to 14 days
outside the range, but never past today. A day with no candidate is left out (for
example, `--filldown` for today). For an inverted pair, the values are compared
after inversion, so `--fillmax` picks the larger of the rates you actually see.

#### Output

Each rate looks like this:

```json
{
    "currency": "USD",
    "reference_currency": "EUR",
    "date": "2023-01-02",
    "granularity": "daily",
    "value": "1.0683",
    "convention": "C"
}
```

- `convention` is `C` when `value` is the number of `currency` units that buy 1
  `reference_currency`, and `I` for the opposite.
- `date` is the first day of the period for monthly and yearly averages.
- `value` is a string, so no precision is lost.
- CSV output has the same fields, as columns.

#### Examples

```bash
# Today's rate, or the last published one if today's isn't out yet
tc rates convert --from USD --fillup

# Every calendar day of December, weekends filled with Friday's rate
tc rates convert --from USD --from-date 2025-12-01 --to-date 2025-12-31 --fillup

# EUR quoted in Kuwaiti dinars (inverted from KWD/EUR)
tc rates convert --from EUR --to KWD --from-date 2025-12-22 --to-date 2025-12-23

# Monthly averages of GBP in USD, to a CSV file
tc rates convert --from GBP --to USD --from-date 2023-01-01 --to-date 2023-12-31 \
    --monthly --format csv --file rates.csv
```

---

## Package reference

Everything below is importable from `twocents` directly, unless noted otherwise.
The library never imports `click`.

### `get_rates`

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

### `list_currencies`

```python
list_currencies(client: RatesClient | None = None) -> list[Currency]
```

Returns every currency known to Banca d'Italia.

### Models

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

### Enums and constants

| Name                   | Values / value                                                 |
| ---------------------- | -------------------------------------------------------------- |
| `Granularity`          | `DAILY="daily"`, `MONTHLY="monthly"`, `YEARLY="yearly"`        |
| `Fill`                 | `UP="up"`, `DOWN="down"`, `MAX="max"`                          |
| `ExchangeConvention`   | `CURRENCY_PER_REFERENCE="C"`, `REFERENCE_PER_CURRENCY="I"`     |
| `Language`             | `IT="it"`, `EN="en"` (language of currency and country names)  |
| `REFERENCE_CURRENCIES` | `("EUR", "USD", "ITL")`                                        |

`Granularity`, `Fill` and `ExchangeConvention` are `StrEnum`s, so plain strings work
wherever they are expected.

### Helpers in `twocents.service`

These are importable from `twocents.service`, not from `twocents`.

| Name                                  | Description                                                                 |
| ------------------------------------- | --------------------------------------------------------------------------- |
| `fill_rates(rates, start, end, fill)` | One rate per day of `[start, end]`, with gaps filled. Rates outside the range only serve as neighbours. |
| `days_between(start, end)`            | Yields every day of `[start, end]`.                                         |
| `months_between(start, end)`          | Yields every `(year, month)` touched by `[start, end]`.                     |
| `FILL_WINDOW`                         | How far outside the range filling looks (`timedelta(days=14)`).             |

### `RatesClient`

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

### Exporters

| Class          | Format                                                         |
| -------------- | -------------------------------------------------------------- |
| `JsonExporter` | Indented JSON array of `to_dict()`                             |
| `CsvExporter`  | CSV of `to_row()` with a header. An empty list writes nothing. |

Both implement the `Exporter` ABC:

- `dump(records, stream)` writes to any text stream, e.g. `sys.stdout`.
- `export(records, path)` writes to a file and overwrites it. The parent directory
  must exist.

`twocents.exporters.EXPORTERS` maps format names to classes.

### Errors

```
TwocentsError
├── APIError                 # .status_code (int | None), .message
└── InvalidDateRangeError    # also a ValueError
```

`APIError.status_code` is `None` when no response was received, for example on a
timeout.

### Logging

Requests are logged at `DEBUG` level to the `twocents` logger, which has a
`NullHandler` by default. To see them, run
`logging.basicConfig(level="DEBUG")` or
`logging.getLogger("twocents").setLevel("DEBUG")`.

---

## Development

```bash
uv sync                 # library, CLI extra and dev tools
uv run tc --help        # or: uv run python -m twocents --help
uv run pytest           # no network needed
uv run ruff check . && uv run ruff format .
uv run ty check
```

P.s. I know Makefile used for aliasing commands is like using a bazooka for a fly, but I like it anyway.
