# Two Cents

Currency exchange rates from [Banca d'Italia](https://tassidicambio.bancaditalia.it),
as a **Python library** and as a **command line tool** (`tc`). No API key is required.

Requires **Python >= 3.13**. The project uses [`uv`](https://docs.astral.sh/uv/) for
dependency and environment management.

## Installation

```bash
git clone https://github.com/FedericoCantarelli/twocents.git
cd twocents
```

| You want…                     | Install with                          | Pulls in           |
| ----------------------------- | ------------------------------------- | ------------------ |
| The library only              | `uv add ./twocents` / `pip install .` | `requests`         |
| The `tc` command              | `uv tool install '.[cli]'`            | `requests`, `click` |
| Both, in a project            | `uv add './twocents[cli]'`            | `requests`, `click` |

Running `tc` without the `cli` extra prints a message explaining how to install it.

## Library usage

```python
import datetime as dt

import twocents

# Daily rates (default), monthly or yearly averages over a date range
rates = twocents.get_rates("USD", dt.date(2023, 1, 1), dt.date(2023, 1, 31))
monthly = twocents.get_rates(
    "GBP",
    dt.date(2022, 1, 1),
    dt.date(2022, 12, 31),
    reference_currency="USD",
    granularity="monthly",
)

for rate in rates:
    print(rate.date, rate.value, rate.currency_per_reference)

# All known currencies
currencies = twocents.list_currencies()

# Export to JSON or CSV (a file path, or any text stream via .dump())
twocents.CsvExporter().export(rates, "rates.csv")
```

Everything returned is a frozen dataclass: `Rate`, `Currency`, `Country`.

- **Reference currency.** Banca d'Italia only quotes against **EUR, USD or ITL**
  (`twocents.REFERENCE_CURRENCIES`).
- **Reading `Rate.value`.** The API publishes some rates as "foreign currency per 1
  EUR" and others the other way round, which is recorded in `Rate.convention`. Use
  `rate.currency_per_reference` or `rate.reference_per_currency` to get a number in
  the direction you want.
- **Errors.** Every exception derives from `twocents.TwocentsError`:
  - `APIError`: network failure or non-200 response, with `.status_code` and `.message`.
  - `InvalidDateRangeError`: start date after end date; also a `ValueError`.
- **Lower-level access.** `twocents.RatesClient` maps one method to each endpoint
  (`get_daily_rates`, `get_daily_time_series`, `get_monthly_average`,
  `get_annual_average`, `get_currencies`). It accepts a `language`, a
  `requests.Session` and a `timeout`.
- **Debug logging.** Logs go to the `twocents` logger, e.g.
  `logging.getLogger("twocents").setLevel("DEBUG")`.

## Running without installing

```bash
uv sync            # installs the library, the CLI extra and dev tools
uv run tc --help   # or: uv run python -m twocents --help
uv run pytest
```

## Commands

The root command is `tc`. It exposes a `version` command and a `rates` command.
Output is JSON on stdout by default; `--format csv` switches to CSV and
`--file PATH` writes to a file instead of stdout.

### `tc version`

Print the installed version.

### `tc rates list`

List all available currencies from Banca d'Italia.

| Option      | Default | Description                                     |
| ----------- | ------- | ----------------------------------------------- |
| `--format`  | `json`  | Output format: `json` or `csv`.                 |
| `--file`    | stdout  | Write the output to this file.                  |
| `--verbose` | off     | Log the requests made (to stderr).              |

### `tc rates convert`

Fetch exchange rates for a currency over a date range.

```bash
tc rates convert --from USD --to EUR --from-date 2023-01-01 --to-date 2023-01-31
```

| Option        | Required | Default | Description                                                  |
| ------------- | -------- | ------- | ------------------------------------------------------------ |
| `--from`      | **yes**  | –       | ISO code of the currency (e.g. `USD`).                       |
| `--to`        | no       | `EUR`   | Reference currency (see below).                              |
| `--from-date` | no       | `--to-date` | Start date, `YYYY-MM-DD`.                                |
| `--to-date`   | no       | today   | End date, `YYYY-MM-DD`.                                      |
| `--daily`     | no       | on      | Daily rates.                                                 |
| `--monthly`   | no       | off     | Monthly averages (one request per month in the range).       |
| `--yearly`    | no       | off     | Yearly averages (one request per year in the range).         |
| `--fillup`    | no       | off     | Daily only: fill days without a rate with the previous rate. |
| `--filldown`  | no       | off     | Daily only: fill days without a rate with the next rate.     |
| `--fillmax`   | no       | off     | Daily only: fill with the larger of the previous/next rate.  |
| `--format`    | no       | `json`  | Output format: `json` or `csv`.                              |
| `--file`      | no       | stdout  | Write the output to this file.                               |
| `--verbose`   | no       | off     | Log the requests made (to stderr).                           |

`--daily`, `--monthly` and `--yearly` are mutually exclusive; the last one given wins.
The same goes for `--fillup`, `--filldown` and `--fillmax`.

Banca d'Italia only quotes against `EUR`, `USD` and `ITL`, so one of `--from`
and `--to` must be one of them. If `--to` isn't (e.g. `--from EUR --to KWD`), the
pair is fetched the other way round and every rate is inverted (`1 / rate`, rounded
to 6 significant digits). The output shows `currency=EUR`, `reference_currency=KWD`.

Without `--from-date` and `--to-date` you get today's rate. With only `--to-date`
you get that single day.

By default only the days Banca d'Italia published a rate for are returned (no
weekends or holidays). A fill flag returns one row per calendar day instead: a day
without a rate gets a copy of a neighbouring rate, looking up to 14 days outside
the range. A day with no candidate is left out (for example `--filldown` for today).

```bash
# Monthly averages of GBP in USD, to a CSV file
tc rates convert --from GBP --to USD --from-date 2023-01-01 --to-date 2023-12-31 --monthly --format csv --file rates.csv

# Today's rate, or the last published one if today's isn't out yet
tc rates convert --from USD --fillup

# Daily series, CSV piped elsewhere
tc rates convert --from USD --from-date 2024-01-01 --to-date 2024-01-31 --format csv | head
```

Each rate is output as:

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

`convention` is `C` when `value` is units of `currency` per 1 `reference_currency`,
and `I` for the opposite. For monthly and yearly averages, `date` is the first day
of the period.

P.s. I know Makefile used for aliasing commands is like using a bazooka for a fly, but I like it anyway.
