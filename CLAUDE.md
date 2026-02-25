# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**python-bcb** is a Python interface to the Brazilian Central Bank (Banco Central do Brasil) open data APIs. It provides access to time series data, exchange rates, market expectations, and financial institution data.

## Python Environment

**This project uses Poetry exclusively.** All Python commands must be run via `poetry run` or inside `poetry shell`. Never invoke `python`, `pytest`, `black`, or any other Python tool directly.

```bash
poetry run python ...
poetry run pytest ...
poetry run black ...
```

## Commands

### Setup
```bash
pip install poetry
poetry install                    # install all dependency groups
poetry install --with test        # install with test dependencies only
```

### Running Tests
```bash
poetry run pytest                            # run all tests
poetry run pytest tests/test_utils.py        # run a single test file
poetry run pytest tests/test_currency.py::test_currency_id  # run a single test
```

Note: Many tests make live HTTP requests to BCB APIs. Tests marked with `@mark.flaky` may fail intermittently due to network issues or API availability.

### Linting / Formatting
```bash
poetry run pycodestyle bcb/                  # lint with pycodestyle
poetry run black bcb/                        # format with black
```

### Docs
```bash
cd docs && make html SPHINXBUILD="poetry run sphinx-build"
```

## Architecture

The package is organized into three main API modules under `bcb/`:

### `bcb.sgs` — SGS Time Series
Fetches time series from the BCB's SGS (Sistema Gerenciador de Séries Temporais) JSON API. The main entry point is `sgs.get(codes, start, end, last, multi, freq)`. Codes can be `int`, `list`, `tuple`, or `dict` for named series. Returns pandas DataFrames with DatetimeIndex or PeriodIndex.

- `bcb/sgs/__init__.py` — `get()` and `get_json()` functions + `SGSCode` class
- `bcb/sgs/regional_economy.py` — wrapper for regional non-performing loan series with pre-mapped SGS codes by state/region

### `bcb.currency` — Currency Exchange Rates
Scrapes the BCB PTAX website for daily bid/ask exchange rates. Uses `requests` + `lxml` for HTML parsing.

- `bcb/currency.py` — `get(symbols, start, end, side, groupby)` returns multi-indexed DataFrames. Module-level `CACHE` dict avoids redundant HTTP requests within a session.

### `bcb.odata` — OData APIs
A generic OData client plus named wrappers for specific BCB OData services (hosted at `olinda.bcb.gov.br`).

- `bcb/odata/framework.py` — Core OData machinery: `ODataService` fetches and parses the `$metadata` XML document (via `lxml`) to discover entity sets, functions, and properties. `ODataQuery` builds and executes queries with chainable methods (`.filter()`, `.orderby()`, `.select()`, `.limit()`, `.skip()`). `ODataProperty` instances support Python comparison operators to create `ODataPropertyFilter` objects.
- `bcb/odata/api.py` — `BaseODataAPI` base class and concrete named classes (`Expectativas`, `PTAX`, `IFDATA`, `TaxaJuros`, `MercadoImobiliario`, `SPI`, etc.). Each subclass just sets `BASE_URL`. The `Endpoint` class (with `EndpointMeta` metaclass) exposes entity properties as attributes, enabling `endpoint.PropertyName >= value` filter syntax. `EndpointQuery.collect()` post-processes date columns into `pd.Timestamp`.
- `bcb/__init__.py` — re-exports all OData API classes at the top level (e.g., `from bcb import PTAX`).

### `bcb.utils`
- `Date` class: normalizes `str`, `datetime`, `date` inputs. Accepts `"today"`/`"now"` strings.
- `BRAZILIAN_REGIONS` / `BRAZILIAN_STATES` constants for geographic lookups.
- `DateInput` type alias used throughout the codebase.

## Key Patterns

- **OData query building**: `api.get_endpoint("EntityName")` returns an `Endpoint`. Call `.get(Property >= value, limit=100)` for one-shot queries, or `.query()` for a chainable `EndpointQuery`.
- **`ODataAPI` for unlisted services**: Pass any valid OData URL directly to `ODataAPI(url)` to access BCB APIs not yet wrapped.
- **All network calls** use either `requests` (SGS, currency) or `httpx` (OData). The OData metadata fetch happens lazily on first `BaseODataAPI` instantiation.
- **`@mark.flaky`**: flaky tests use the `flaky` library with `max_runs` retries to handle transient API failures.
