# Two Cents

A simple command line tool for fetching currency exchange rates from
[Banca d'Italia](https://tassidicambio.bancaditalia.it). No API key is required.

Requires **Python >= 3.13**. The project uses [`uv`](https://docs.astral.sh/uv/) for
dependency and environment management.

## Installation

Install the package (and its `twocents` command) from the repository:

```bash
git clone https://github.com/FedericoCantarelli/twocents.git
cd twocents

# Install into your current environment as a CLI tool
uv tool install .
```

After installation the CLI is available as `twocents`:

```bash
twocents --help
```

## Running without installing

You can run the CLI straight from a clone without installing the package:

```bash
# Sync the environment from the lockfile, then run through uv
uv sync
uv run twocents --help
```

## Commands

The root command is `twocents`. It exposes a `version` command and a `rates` command.

### `twocents version`

Print the installed CLI version.

```bash
twocents version
```

### `twocents rates list`

List all available currencies from Banca d'Italia.

```bash
twocents rates list
```

| Option      | Required | Default | Description                                                              |
| ----------- | -------- | ------- | ------------------------------------------------------------------------ |
| `--format`  | no       | stdout  | Output format: `json` or `csv`. Requires `--file`.                       |
| `--file`    | no*      | –       | Destination file path. Required when `--format` is set.                  |
| `--verbose` | no       | off     | Show verbose output (logs the requests made).                            |

### `twocents rates convert`

Fetch exchange rates for a currency pair over a date range.

```bash
twocents rates convert --from USD --to EUR --from-date 2023-01-01 --to-date 2023-01-31 --daily
```

| Option        | Required | Default    | Description                                                             |
| ------------- | -------- | ---------- | ---------------------------------------------------------------------- |
| `--from`      | **yes**  | –          | Base currency ISO code (e.g. `USD`).                                    |
| `--to`        | no       | `EUR`      | Target currency ISO code.                                              |
| `--from-date` | **yes**  | –          | Start date in `YYYY-MM-DD` format.                                     |
| `--to-date`   | no       | today      | End date in `YYYY-MM-DD` format. Defaults to the current date.         |
| `--daily`     | no       | on         | Daily granularity (used unless another granularity is chosen).        |
| `--monthly`   | no       | off        | Monthly average granularity.                                          |
| `--yearly`    | no       | off        | Yearly average granularity.                                           |
| `--format`    | no       | stdout     | Output format: `json` or `csv`. Requires `--file`.                    |
| `--file`      | no*      | –          | Destination file path. Required when `--format` is set.               |
| `--verbose`   | no       | off        | Show verbose output.                                                  |

By default output is printed to stdout as JSON. To write it to a file, pass both
`--format` and `--file`:

```bash
# Export a monthly series to a CSV file
twocents rates convert --from GBP --to EUR --from-date 2023-01-01 --to-date 2023-12-31 --monthly --format csv --file rates.csv

# Export a daily series to a JSON file
twocents rates convert --from USD --from-date 2024-01-01 --to-date 2024-01-31 --daily --format json --file rates.json
```
