# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**python-bcb** is a Python interface to the Brazilian Central Bank (Banco Central do Brasil) open data APIs. It provides access to time series data, exchange rates, market expectations, and financial institution data.

## Python Environment

**This project uses uv exclusively.** All Python commands must be run via `uv run`. Never invoke `python`, `pytest`, `ruff`, or any other Python tool directly.

```bash
uv run python ...
uv run pytest ...
uv run ruff ...
```

## Commands

### Setup
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh  # install uv
uv sync                           # install all dependency groups
uv sync --group test              # install with test dependencies only
```

### Running Tests
```bash
uv run pytest                            # run all tests
uv run pytest tests/test_utils.py        # run a single test file
uv run pytest tests/test_currency.py::test_currency_id  # run a single test
```

Note: Many tests make live HTTP requests to BCB APIs. Tests marked with `@mark.flaky` may fail intermittently due to network issues or API availability.

### Linting / Formatting
```bash
uv run ruff check bcb/                   # lint with ruff
uv run ruff format bcb/                  # format with ruff
```

### Docs
```bash
cd docs && uv run sphinx-build -b html . _build/html
```

## Architecture

The package is organized into three main API modules under `bcb/`:

### `bcb.sgs` — SGS Time Series
Fetches time series from the BCB's SGS (Sistema Gerenciador de Séries Temporais) JSON API. The main entry point is `sgs.get(codes, start, end, last, multi, freq)`. Codes can be `int`, `list`, `tuple`, or `dict` for named series. Returns pandas DataFrames with DatetimeIndex or PeriodIndex.

- `bcb/sgs/__init__.py` — `get()` and `get_json()` functions + `SGSCode` class
- `bcb/sgs/regional_economy.py` — wrapper for regional non-performing loan series with pre-mapped SGS codes by state/region

### `bcb.currency` — Currency Exchange Rates
Scrapes the BCB PTAX website for daily bid/ask exchange rates. Uses `httpx` + `lxml` for HTML parsing.

- `bcb/currency.py` — `get(symbols, start, end, side, groupby)` returns multi-indexed DataFrames. Module-level `_CACHE` dict avoids redundant HTTP requests within a session.

### `bcb.odata` — OData APIs
A generic OData client plus named wrappers for specific BCB OData services (hosted at `olinda.bcb.gov.br`).

- `bcb/odata/framework.py` — Core OData machinery: `ODataService` fetches and parses the `$metadata` XML document (via `lxml`) to discover entity sets, functions, and properties. `ODataQuery` builds and executes queries with chainable methods (`.filter()`, `.orderby()`, `.select()`, `.limit()`, `.skip()`). `ODataProperty` instances support Python comparison operators to create `ODataPropertyFilter` objects.
- `bcb/odata/api.py` — `BaseODataAPI` base class and concrete named classes (`Expectativas`, `PTAX`, `IFDATA`, `TaxaJuros`, `MercadoImobiliario`, `SPI`, etc.). Each subclass just sets `BASE_URL`. The `Endpoint` class (with `EndpointMeta` metaclass) exposes entity properties as attributes, enabling `endpoint.PropertyName >= value` filter syntax. `EndpointQuery.collect()` post-processes date columns into `pd.Timestamp`.
- `bcb/__init__.py` — re-exports all OData API classes at the top level (e.g., `from bcb import PTAX`).

### `bcb.utils`
- `Date` class: normalizes `str`, `datetime`, `date` inputs. Accepts `"today"`/`"now"` strings.
- `BRAZILIAN_REGIONS` / `BRAZILIAN_STATES` constants for geographic lookups.
- `DateInput` type alias used throughout the codebase.

## Definition of Done

Every task must pass all of the following before it is considered complete:

```bash
uv run pytest -m "not integration"       # all unit tests pass
uv run ruff check bcb/ tests/            # no lint errors
uv run ruff format --check bcb/ tests/   # code is formatted
uv run mypy bcb/                         # no type errors
```

## Key Patterns

- **OData query building**: `api.get_endpoint("EntityName")` returns an `Endpoint`. Call `.get(Property >= value, limit=100)` for one-shot queries, or `.query()` for a chainable `EndpointQuery`.
- **`ODataAPI` for unlisted services**: Pass any valid OData URL directly to `ODataAPI(url)` to access BCB APIs not yet wrapped.
- **All network calls** use `httpx` (sync) with `follow_redirects=True`. The OData metadata fetch happens lazily on first `BaseODataAPI` instantiation.
- **`@mark.flaky`**: flaky tests use the `flaky` library with `max_runs` retries to handle transient API failures.
