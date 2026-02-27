# Changelog

## [Unreleased]

## [0.3.5] - 2026-02-27
- Added `output="text"` parameter to `sgs.get()`, `currency.get()`, `EndpointQuery.collect()`, and `Endpoint.get()` — returns raw API response text (JSON for SGS and OData, CSV for currency) instead of a DataFrame; multi-code/symbol calls return `dict[key, str]`; default behavior unchanged
- Migrated from Poetry to uv for package management (PEP 621 + hatchling build backend)
- Replaced `black` and `pycodestyle` with `ruff` for linting and formatting

## [0.3.4] - 2026-02-25
- Replaced `requests` with `httpx` as the sole HTTP client across all modules
- Added custom exceptions: `BCBError`, `BCBAPIError`, `CurrencyNotFoundError`, `SGSError`, `ODataError`
- Added full type annotations with `mypy --strict` compliance
- Added `DATE_COLUMNS` class attribute to `BaseODataAPI` for configurable date column detection
- Renamed internal `CACHE` to `_CACHE` in `currency` module; added `currency.clear_cache()`
- Overhauled test suite with mocked HTTP unit tests and a separate `tests/integration/` layer
- Added CI/CD workflows: test matrix (Python 3.10–3.12), lint (black + mypy), Sphinx docs build
- Fixed Sphinx docs build: updated `taxajuros` example to match BCB API rename of `'Cheque especial - Pré-fixado'` → `'Cheque especial - Prefixado'`

## [0.3.3] - 2025-04-21
- Improved error handling in SGS API
- Added type hints to the bcb.sgs and sgs.currency modules
- Added function sgs.get_json to retrieve raw JSON data returned from SGS API

## [0.3.2] - 2025-03-01
- Poetry lock file updated
- Replaced http with https in SGS URL

## [0.3.1] - 2024-12-24
- Add Regional economy series support (tks @anapaulagomes)

## [0.3.0] - 2024-06-12
- Dependencies updated

## [0.2.0] - 2023-07-22
- Date columns of some OData API endpoints are now formatted in the returned Dataframe (Issue #3)
- New methods ODataQuery.raw and ODataQuery.text

## [0.1.9] - 2023-06-26
- Created class bcb.ODataAPI to directly wrap OData APIs
- Updated documentation
- Updated pyproject.toml

## [0.1.8] - 2022-09-10
- Updated documentation
- Migrated to poetry

## [0.1.7] - 2022-01-22
- Added httpx to install_requirements
- Updated docs
- sgs.TaxaJuros upgraded to v2

## [0.1.6] - 2022-01-16
- Updated README
- Updated requirements files including `httpx`
- Added `autosummary_generate` to sphinx conf.py


## [0.1.5] - 2022-01-16
- Implemented the definetive wraper for OData APIs.
  - A few APIs have been unlocked: Expectativas, PTAX, taxaJuros, MercadoImobiliario, SPI
- Updated documentation

## [0.1.4] - 2021-12-27
- Changed arguments start_date and end_date to start and end to bring conformity with commom python data libraries like Quandl and pandas-datareader, for example.
- bcb.currency.get multi argument, which refers to multivariate time series returned (defaults to True)
- bcb.sgs.get groupby argument
- Sphinx docs implemented

## [0.1.3] - 2021-04-14
- BUG fix in get_valid_currency_list: recurrent ConnectionError
- Added side and group_by arguments to currency.get function
- New notebooks with examples
- Added join argument to sgs.get function

## [0.1.2] - 2021-01-25
- New sgs module downloads time series from SGS BACEN's site
- Notebooks created to show a few examples
- Date class moved to utils module

## [0.1.1] - 2021-01-16

- Bug fixes

## [0.1.0] - 2021-01-16

- First commit
- currency module downloads currency rates quoted in Brazilian Real (BRL)