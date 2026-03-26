# Changelog

## [0.3.6] - 2026-03-26

### Added
- **Async API Support** — All modules now have async counterparts: `sgs.async_get()`, `sgs.async_get_json()`, `currency.async_get()`, `ODataQuery.async_text()`, `ODataQuery.async_collect()`, `Endpoint.async_get()` for concurrent data fetching with `asyncio.gather()`
- **Logging Infrastructure** — Debug-level logging for all HTTP requests/responses (URL, status, response length) and warning-level logging for connection retry attempts across currency, sgs, and odata modules
- **Comprehensive Test Coverage** — Added 36 new tests: 12 negative tests for currency API (404/429/500 errors, malformed CSV), 15 negative tests for SGS API (malformed JSON, invalid inputs), 9 async tests; total 103 unit tests with proper mock isolation
- **Example Scripts** — Added `examples/` directory with 4 comprehensive usage examples: SGS time series, currency exchange rates, OData queries with filters/sorting, and async API usage (all translated to Portuguese)
- **Async Documentation** — New `docs/async.rst` with comprehensive guide to async APIs, examples with `asyncio.gather()`, performance comparisons, and semaphore patterns
- **Portuguese Documentation** — Translated README.md and all example scripts to Portuguese (docstrings and comments)
- **Enhanced Documentation** — Added "Which Module to Use?" decision table and FAQ section to README covering module differences, data coverage, async usage, error handling, logging setup, caching, and long-running applications
- **Factory Functions** in tests/conftest.py — Parameterizable mock data generators: `make_currency_id_list_html()`, `make_currency_list_csv()`, `make_currency_rate_csv()`, `make_sgs_response()`, `make_odata_metadata_xml()`, `make_odata_query_response()`
- **Cache Clearing Fixtures** — Added automatic OData metadata cache clearing between tests to prevent pytest-httpx mock assertion errors
- **Sidebar Navigation** — Configured Furo theme with global sidebar navigation appearing on all documentation pages

### Changed
- **Exception Handling** — Updated `bcb/currency.py` `get()` function to wrap `_get_symbol()` calls in try-except, allowing skipping of missing currencies while maintaining fail-fast for internal errors (per Phase 2 architecture)
- **Test Organization** — Added `clear_odata_cache` fixture for proper test isolation; fixed `test_clear_cache` to use new `_ThreadSafeCache` API; renamed `test_get_symbol_unknown_currency_returns_none` to `test_get_symbol_unknown_currency_raises` to match fail-fast semantics
- **Cache Management** — Added explicit `_CacheKey` namedtuple for structured cache keys in currency module; enhanced thread-safe cache with clear, get, set operations

### Fixed
- **Cache State Issues** — Resolved pytest-httpx unused mock assertions by implementing `clear_odata_cache` fixture that clears global `_METADATA_CACHE` between tests
- **Test Failures** — Fixed 2 failing tests (`test_clear_cache`, `test_get_symbol_unknown_currency_returns_none`) to work with Phase 2 architecture changes and Phase 3 cache refactor
- **Example API Constraints** — Updated examples to respect API limits: `last=20` (not 30) for SGS; fixed OData filter syntax and `select()` variadic arguments

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