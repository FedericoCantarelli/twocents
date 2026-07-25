# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`twocents` is a Python CLI (Click-based) that fetches currency exchange rates from
Banca d'Italia's public REST API (`tassidicambio.bancaditalia.it`). No API key is
required. Requires Python >= 3.13. Dependencies are managed with `uv`.

## Commands

```bash
# Install / sync the environment (creates .venv from uv.lock)
uv sync

# Run the CLI (entry point is `tc`, mapped to twocents:main)
uv run tc --help
uv run tc version
uv run tc rates list
uv run tc rates convert --from USD --to EUR --from-date 2023-01-01 --to-date 2023-01-31 --daily

# Lint & format (ruff is configured via ruff.toml)
uv run ruff check .
uv run ruff format .

# Type check (mypy is used; see .mypy_cache)
uv run mypy src
```

There is currently no test suite in the repository.

## Architecture

The package lives under `src/twocents/` and is organized into four layers:

- **`__init__.py`** — defines the root Click group `main` and registers subcommands.
  `main` is the console-script entry point (`tc`).
- **`commands/`** — Click command definitions, one module per command group.
  `rates.py` holds the `rates` group with `list` and `convert` subcommands and owns all
  CLI-level validation (date parsing, `--format`/`--file` pairing, granularity flags).
  Commands orchestrate: call `RatesClient`, then hand the result to an exporter.
- **`rates/client.py`** — `RatesClient` wraps the Banca d'Italia REST endpoints
  (`currencies`, `dailyRates`, `dailyTimeSeries`, `monthlyAverageRates`,
  `annualAverageRates`). Each method builds an endpoint string and delegates to
  `_make_get_request`, which appends the `lang` query param and returns parsed JSON.
- **`exporters/`** — output strategies. `base.Exporter` is the ABC (`export(file_path)`);
  `JsonExporter` and `CsvExporter` write to files; `StdOutExporter` prints JSON to the
  terminal (note: its `export()` takes no arguments, unlike the file exporters).
- **`utils/`** — `parse_datetime`/`safe_parse_datetime` (strict `YYYY-MM-DD` parsing) and
  `pretty_print.py` (ANSI-colored print helpers and `print_verbose`).

### Key conventions and gotchas

- **Verbose output** is toggled by setting the `VERBOSE` env var; commands set it from a
  `--verbose` flag, and `print_verbose` only prints when it is set.
- **`_exclude_fields([...])` decorator** on `RatesClient` methods strips keys (e.g.
  `resultsInfo`) from the returned dict before it reaches the caller.
- **Monthly granularity** in `convert` is built client-side: it enumerates every
  (year, month) between the two dates and calls `get_avg_monthly_exchange_rates` per
  month, extending a flat list from each response's `rates` key. Daily granularity uses a
  single time-series call. Note `--daily` defaults to `True`, so it runs unless another
  flag path is taken.
- **Ruff** (`ruff.toml`) enforces a strict rule set including pydocstyle (Google
  convention), 80-char lines, single-line imports (isort `force-single-line`), and banned
  relative imports — always use absolute `twocents.*` imports. `# noqa: T201` is used to
  allow `print` in `pretty_print.py`.
