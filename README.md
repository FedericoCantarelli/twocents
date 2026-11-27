# Two Cents

Currency exchange rates from [Banca d'Italia](https://tassidicambio.bancaditalia.it), no API key is required.

Both as a **Python module** and as a **CLI**. 

- [Installation](#installation)
- [Quick start](#quick-start)
- [CLI reference](#cli-reference)
- [Package reference](#package-reference)
- [Development](#development)

## Installation

The package is published on PyPI as
[`twocents-xchange-rate`](https://pypi.org/project/twocents-xchange-rate/);
it is imported as `twocents`.

| You want…          | Install with                                                                    |
| ------------------ | ------------------------------------------------------------------------------- |
| The library only   | `uv add twocents-xchange-rate` / `pip install twocents-xchange-rate`            |
| The `tc` command   | `uv tool install 'twocents-xchange-rate[cli]'`                                  |
| Both, in a project | `uv add 'twocents-xchange-rate[cli]'` / `pip install 'twocents-xchange-rate[cli]'` |

Running `tc` without the `cli` extra prints a message explaining how to install it.

To install from source instead:

```bash
git clone https://github.com/FedericoCantarelli/twocents.git
cd twocents
uv tool install '.[cli]'
```

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

P.s. I know Makefile used for aliasing commands is like using a bazooka for a fly, but I like it anyway.
