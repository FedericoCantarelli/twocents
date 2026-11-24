# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`twocents` fetches currency exchange rates from Banca d'Italia's public REST API
(`tassidicambio.bancaditalia.it`). It is both a Python library (depends only on
`requests`) and a Click CLI (`tc`, behind the `cli` extra). No API key is required.
Requires Python >= 3.13. Dependencies are managed with `uv`; `uv sync` installs the
`cli` extra via the dev group.

## Commands

```bash
# Install / sync the environment (creates .venv from uv.lock)
uv sync

# Run the CLI (entry point `tc` -> twocents.cli:main)
uv run tc --help
uv run tc version
uv run tc rates list
uv run tc rates convert --from USD --to EUR --from-date 2023-01-01 --to-date 2023-01-31 --daily

# Lint & format (ruff is configured via ruff.toml)
uv run ruff check .
uv run ruff format .

# Type check (ty)
uv run ty check

# Tests (pytest, no network: see `fake_session` in tests/conftest.py)
uv run pytest
uv run pytest tests/test_cli.py -k monthly
```

## Architecture

`src/twocents/` is split into a click-free **library** and a **CLI** subpackage.
The library must never import click; `tests/test_package.py` enforces this.

Library:
- **`__init__.py`**: the public API (`__all__`) and `__version__`. Re-exports
  everything below, and attaches a `NullHandler` to the `twocents` logger.
- **`client.py`**: `RatesClient`, one method per endpoint (`currencies`, `dailyRates`,
  `dailyTimeSeries`, `monthlyAverageRates`, `annualAverageRates`). It uses a
  `requests.Session` with `params=`, adds `lang`, and parses responses into models.
  Network failures and non-200 responses raise `APIError`.
- **`service.py`**: the high-level entry points `get_rates()` and `list_currencies()`.
  It validates input and handles ranges: daily is one time-series call, monthly and
  yearly are one call per month or year.
- **`models.py`**: frozen dataclasses `Rate`, `Currency`, `Country`, plus the enums
  `Granularity` and `ExchangeConvention`. Each model has `from_api()`, `to_dict()`
  (JSON) and `to_row()` (flat, for CSV).
- **`exporters.py`**: `Exporter` ABC with `dump(records, stream)` and
  `export(records, path)`, implemented by `JsonExporter` and `CsvExporter`.
  `EXPORTERS` maps format names to classes.
- **`errors.py`**: `TwocentsError`, with subclasses `APIError` and
  `InvalidDateRangeError` (the latter is also a `ValueError`).

CLI (`cli/`, entry point `tc = twocents.cli:main`, also `python -m twocents`):
- **`cli/__init__.py`**: the root group. It exits with an install hint if click is
  missing.
- **`cli/rates.py`**: `list` and `convert`. These only parse options and call
  `service`.
- **`cli/output.py`**: shared helpers. `verbose_option` adds a logging handler to
  stderr for one invocation. `output_options` adds `--format` and `--file`.
  `library_errors` maps `TwocentsError` to click errors. `write_records` writes the
  output.

### Key conventions and gotchas

- **API quirks.** `currencyIsoCode` (our `reference_currency`) only accepts EUR, USD or
  ITL; when only `currency` is one of those, `get_rates` swaps the pair and returns
  `Rate.inverted()` copies (inversion happens before filling). `Rate.value`
  direction depends on `exchangeConventionCode` (`C` or `I`); for
  `dailyTimeSeries` that code and `isoCode` are only in `resultsInfo`, which the
  client passes to `Rate.from_api(defaults=...)`. Unknown currencies and empty ranges
  return 200 with no rates.
- **Granularity flags** `--daily/--monthly/--yearly` share one `granularity` dest via
  `flag_value`, so exactly one applies. `--fillup/--filldown/--fillmax` share a `fill`
  dest the same way (`models.Fill`). They are daily only: `service._filled_daily`
  fetches up to `FILL_WINDOW` beyond the range (never past today), then
  `fill_rates` builds one rate per calendar day.
- **Dates**: `get_rates` defaults `end` to today and `start` to `end`, so with no
  dates you get today's rate.
- **Tests** never hit the network. The `fake_session` fixture replaces
  `requests.Session` and routes responses by endpoint. Realistic payload builders are
  in `tests/payloads.py`.
- **Ruff** (`ruff.toml`, target py313) enforces a strict rule set including pydocstyle
  (Google convention; not enforced in `tests/`), 80-char lines, single-line imports
  (isort `force-single-line`), and banned relative imports. Always use absolute
  `twocents.*` imports.
