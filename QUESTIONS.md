# QUESTIONS.md — Architectural & Technical Review

This document captures all architectural, refactoring, performance, security, and correctness questions found during a full code review of **python-bcb**.

---

## 1. HTTP Client Lifecycle

### Q1.1 — Module-level `httpx.Client` and `httpx.AsyncClient` are never closed

In `bcb/http.py`, `_CLIENT` and `_ASYNC_CLIENT` are instantiated at module import time and live forever. `close_async_client()` exists but there is no `close_client()` for the sync client. The sync `httpx.Client` holds open TCP connections indefinitely.

**Should we add a `close_client()` function (and/or an `atexit` hook) for the sync client to mirror `close_async_client()`?**

### Q1.2 — `close_async_client()` has fragile event-loop detection

`close_async_client()` tries `asyncio.get_event_loop()`, then `loop.is_running()`, then `asyncio.run()`. On Python 3.10+ `get_event_loop()` in a non-async context emits a `DeprecationWarning` and will eventually stop working. Also, `asyncio.create_task()` does not block — the caller has no guarantee the client actually closed.

**Should this be simplified (e.g. just expose an `async aclose()` and document that the user should call it in their async cleanup)?**

### Q1.3 — Shared global clients are not safe for `fork()`

If a process forks (e.g. `multiprocessing`), the child inherits the parent's `httpx.Client` with shared sockets. This can cause cryptic connection errors.

**Is multiprocessing a supported use case? If so, should we document the limitation or re-create clients per-process?**

---

## 2. Retry & Resilience

### Q2.1 — `with_retry` is defined but never used

`bcb/http.py` defines `with_retry()` wrapping `tenacity.retry`, but no call site in the codebase actually uses it. Meanwhile, `_get_valid_currency_list()` hand-rolls its own recursive retry logic with `n >= 3`.

**Should we either (a) apply `with_retry` to all HTTP-calling functions, or (b) remove the dead code?**

### Q2.2 — `_get_valid_currency_list` uses recursion for retry + rollback

The function recurses up to `3 * 30 = 90` stack frames in the worst case (3 retries per day x 30 days rollback). Python's default recursion limit is 1000, but this is still unnecessarily deep.

**Should this be rewritten as iterative loops (one for day rollback, one for connection retries)?**

### Q2.3 — No retry logic in SGS or OData modules

SGS (`get_json`) and OData (`ODataQuery.text`) make single HTTP requests with no retry. Transient 5xx or timeout errors cause immediate failure.

**Should we add retry logic (via the existing `with_retry` decorator or similar) to SGS and OData HTTP calls?**

### Q2.4 — `tenacity` is imported but only used to define `_retry_decorator`

Since `_retry_decorator` / `with_retry` is never applied anywhere, `tenacity` is effectively an unused runtime dependency.

**Should we either start using it or remove it from `[project.dependencies]`?**

---

## 3. Error Handling

### Q3.1 — `_fetch_symbol_response` checks Content-Type before status code

In `bcb/currency.py:355-387`, the function first checks if `Content-Type` starts with `text/html` (to parse an error page), then checks `res.status_code`. If the server returns a 5xx with `text/html` content type, the code will try to parse the HTML error div first — and may crash with an `IndexError` on `doc.xpath(xpath)[0]` if the HTML structure doesn't match.

**Should status code be checked first, and the HTML error parsing be a fallback only for 200 responses with unexpected content?**

### Q3.2 — Bare `except Exception` in `_get_valid_currency_list` and async variant

Line 241 catches all exceptions including `KeyboardInterrupt` (via the `Exception` base). More importantly, it silently retries on any error (including programming bugs like `TypeError`), making debugging harder.

**Should the except clause be narrowed to `httpx.TransportError` or similar network-specific exceptions?**

### Q3.3 — `get_non_performing_loans_codes` raises bare `Exception`

In `bcb/sgs/regional_economy.py:150`, the function raises `Exception(...)` instead of a custom exception.

**Should this use `ValueError` or a custom `BCBError` subclass for consistency?**

### Q3.4 — Mixing states and regions in `get_non_performing_loans_codes` silently fails

If the user passes `["BA", "N"]` (a state AND a region), the function checks `any(...)` for states first, enters the `is_state` branch, and then `codes[location] = non_performing_loans_by_location["N"]` raises `KeyError` because "N" is not in the state dict.

**Should this be validated upfront to give a clear error message about mixing states and regions?**

### Q3.5 — `_codes()` silently returns empty for unsupported types

In `bcb/sgs/__init__.py:119`, if `codes` is an unexpected type (e.g. `float`, `set`), the generator simply yields nothing. Downstream, this causes a confusing `ValueError: No objects to concatenate` from pandas.

**Should `_codes()` raise a `TypeError` for unsupported input types?**

### Q3.6 — OData `text()` and `async_text()` don't check HTTP status codes

In `bcb/odata/framework.py:551-567`, the OData query just returns `res.text` without checking `res.status_code`. A 404, 429, or 500 from the OData API is silently returned as if it were valid JSON, which then causes a confusing `json.JSONDecodeError` downstream.

**Should we add status code validation (and raise `ODataError` or `BCBAPIError`) in the OData HTTP layer?**

### Q3.7 — `async_get` in currency doesn't handle exceptions from `asyncio.gather`

In `bcb/currency.py:909-912`, `asyncio.gather()` is called without `return_exceptions=True`. If any symbol fetch fails, the entire gather fails. The sync version uses try/except per symbol to skip missing currencies.

**Should `return_exceptions=True` be used (with per-result error checking), or should individual tasks be wrapped in try/except?**

### Q3.8 — `BCBAPIServerError` exception is defined but never raised

`bcb/exceptions.py:28-31` defines `BCBAPIServerError` but the codebase always raises `BCBAPIError` for 5xx responses instead.

**Should 5xx responses use `BCBAPIServerError`, or should the unused class be removed?**

---

## 4. Caching

### Q4.1 — Currency cache has no TTL/expiration

The `_ThreadSafeCache` stores currency ID lists and currency master data indefinitely (for the session lifetime). If a long-running process (e.g. a web server) uses the library, the cached data could become stale (new currencies added, old ones delisted).

**Should the cache support a configurable TTL, or is `clear_cache()` sufficient?**

### Q4.2 — OData metadata cache (`_METADATA_CACHE`) has no eviction

`bcb/odata/framework.py:20-21` caches metadata per URL indefinitely. If the BCB changes the schema, the cache will serve stale metadata until the process restarts.

**Should there be a `clear_metadata_cache()` public function, or a TTL?**

### Q4.3 — `_ThreadSafeCache` uses `threading.RLock` but async code shares the same cache

The async currency functions (`_async_currency_id_list`, `_async_get_currency_list`) call `cache.get()` and `cache.set()` which acquire a `threading.RLock`. In an async context, this blocks the event loop while holding the lock.

**Should the async code use `asyncio.Lock` instead, or is the lock contention negligible for the use case?**

### Q4.4 — No cache for SGS responses

SGS calls are never cached — repeated calls for the same series and date range hit the API every time.

**Is this intentional? Would a simple response cache (similar to currency) be beneficial?**

---

## 5. `Date` Utility Class

### Q5.1 — `Date.__init__` parameter shadows built-in `format`

The `format` parameter in `Date.__init__` shadows the Python built-in `format()`. Similarly, the `Date.format()` method uses `fmts` as parameter name.

**Should the init parameter be renamed to `fmt` or `date_format` for clarity?**

### Q5.2 — `Date` doesn't support `pd.Timestamp`

The docstrings for `sgs.get()` and `currency.get()` mention `Timestamp` as a valid input type. However, `Date.__init__` only handles `str`, `datetime`, `date`, and `Date`. A `pd.Timestamp` would fall through to the `else: raise ValueError` branch.

**Should `Date` handle `pd.Timestamp` (which is a `datetime` subclass, so it may already work — but worth verifying)?**

### Q5.3 — `Date` doesn't have a `__hash__` method

`Date` implements `__eq__` but not `__hash__`, making it unhashable. This means `Date` objects can't be used as dict keys or in sets.

**Is this intentional, or should `__hash__` delegate to `self.date.__hash__()`?**

---

## 6. Type Safety & API Design

### Q6.1 — `sgs.get()` return type is a union of 4 types

`sgs.get()` returns `Union[pd.DataFrame, List[pd.DataFrame], str, Dict[int, str]]` depending on `output`, `multi`, and the number of codes. This makes it hard for callers to know what they'll get without runtime checks.

**Would it be better to have separate functions (e.g. `get_text()`, `get_many()`) or at least narrow the overloads?**

### Q6.2 — `side` and `groupby` in `currency.get()` are untyped strings

`side` accepts `"ask"`, `"bid"`, `"both"` and `groupby` accepts `"symbol"`, `"side"`, but both are typed as `str`. Invalid values are only caught at runtime deep in the function.

**Should these use `Literal` types and be validated early?**

### Q6.3 — `output` parameter across all modules is untyped `str`

`output` accepts `"dataframe"` or `"text"` across sgs, currency, and odata, but is typed as plain `str`.

**Should this use `Literal["dataframe", "text"]` consistently?**

### Q6.4 — `Endpoint.get()` and `Endpoint.async_get()` are mostly duplicated code

The two methods in `bcb/odata/api.py` (lines 149-226 and 248-326) are nearly identical except for the `await` keyword.

**Should the shared query-building logic be extracted into a private method?**

### Q6.5 — `EndpointQuery.collect()` and `EndpointQuery.async_collect()` are duplicated

Same pattern as above — the date column conversion logic is duplicated between sync and async versions (lines 62-111 in `bcb/odata/api.py`).

**Should the date conversion be a separate method called by both?**

### Q6.6 — `regional_economy` SGS code dicts use `str` values instead of `int`

All the `NON_PERFORMING_LOANS_BY_*` dicts map state/region to string codes (e.g. `"15888"` instead of `15888`). These are then passed to `sgs.get()` which accepts `int | str`.

**Should the constants be `int` for consistency with the rest of the API?**

---

## 7. OData Framework

### Q7.1 — `ODataQuery.reset()` doesn't reset `_select` or `_raw`

`reset()` clears `_filter`, `_orderby`, and `_params`, but leaves `_select` and `_raw` intact. After `Endpoint.get()` calls `_query.reset()`, these fields retain their values. Since a new `EndpointQuery` is created each time, this is harmless now — but `reset()` is misleading.

**Should `reset()` clear all query state, or should it be removed entirely since queries are not reused?**

### Q7.2 — `ODataQuery._build_parameters()` always overrides `$format` from `_params`

`_build_parameters()` starts with `params = {"$format": self._params.get("$format", "json")}`, then later does `params.update(self._params)`. This means `$format` is set twice if it was explicitly set. The logic works but is confusing.

**Should this be simplified to just use `self._params` directly with a default?**

### Q7.3 — Query string is built manually instead of using `httpx` params

In `ODataQuery.text()`, the query string is manually constructed with `urllib.parse.quote` and string concatenation instead of passing params to `httpx.Client.get(params=...)`.

**Should we let httpx handle URL encoding for correctness and simplicity?**

### Q7.4 — `ODataService.__init__` makes two HTTP requests eagerly

Instantiating any `BaseODataAPI` subclass (like `Expectativas()`) immediately fetches the service root JSON AND the `$metadata` XML. This means `api = Expectativas()` is a blocking network call.

**Should metadata loading be lazy (on first query), to avoid network calls at import/construction time?**

### Q7.5 — `EndpointMeta` metaclass sets attributes on every `Endpoint.__call__`

The `EndpointMeta.__call__` method sets OData properties as attributes on the `Endpoint` instance. This uses `setattr` in a loop on every instantiation.

**Is the metaclass necessary, or could this be done in `Endpoint.__init__`?**

### Q7.6 — `str_types()` function uses a parameter named `type` shadowing built-in

`bcb/odata/framework.py:38` defines `def str_types(type: str) -> str:` which shadows the built-in `type()`.

**Should the parameter be renamed to `edm_type` or similar?**

### Q7.7 — `ODataProperty.name` and `ODataProperty.type` return `Optional[str]`

Properties have `Optional[str]` return types for `name` and `type`, but they're used everywhere without null checks (e.g. `f"{self.obj.name} {self.operator} ..."` in `ODataPropertyFilter.statement()`).

**Should these be non-optional (validated at construction), or should callers handle `None`?**

### Q7.8 — No pagination support in OData queries

OData APIs typically return paginated results with `@odata.nextLink`. The current implementation fetches a single page and returns it. Large result sets are silently truncated.

**Should the framework support automatic pagination (following `@odata.nextLink`) or at least document the limitation?**

---

## 8. Currency Module

### Q8.1 — `_get_currency_id` merges two DataFrames on every call

`_get_currency_id()` calls `_currency_id_list()` and `get_currency_list()`, then does `pd.merge(id_list, all_currencies, on=["name"])` to find the currency ID. This merge happens on every symbol lookup, even though the data is cached.

**Should the merged result be cached as well?**

### Q8.2 — `_get_currency_id` returns `matches.max()` — why max?

When there are multiple matching IDs for a symbol, `matches.max()` is used. This implies there can be duplicates and we want the highest ID.

**Why `max()` specifically? Is this documented behavior from BCB, or a heuristic?**

### Q8.3 — Currency CSV parsing assumes exactly 8 columns

`_validate_currency_csv()` hardcodes `len(df.columns) != 8`. If BCB adds or removes a column from their CSV format, the library breaks.

**Should the validation be more flexible (e.g. check for minimum required columns by position)?**

### Q8.4 — The currency module mixes two different BCB data sources

`_currency_id_list()` scrapes HTML from `ptax.bcb.gov.br`, while `get_currency_list()` downloads a CSV from `www4.bcb.gov.br`. These are joined by `name` field, which assumes the naming is consistent across both sources.

**Is this fragile? Has the naming ever diverged?**

### Q8.5 — No Content-Type header check for the CSV download in `_get_valid_currency_list`

The function checks status code but not Content-Type. A 200 response with HTML content (e.g. a redirect page) would be passed to `pd.read_csv` and cause a confusing error.

**Should Content-Type be validated?**

### Q8.6 — `currency.get()` silently skips `CurrencyNotFoundError` for individual symbols

When fetching multiple symbols, `CurrencyNotFoundError` is caught and the symbol is silently skipped. But other exceptions (like `BCBAPIError` for network issues) would propagate and abort the whole call.

**Is this the intended behavior? Should the user be warned about skipped symbols?**

---

## 9. SGS Module

### Q9.1 — `sgs.get()` calls `get_json()` twice for DataFrame output

For each code, `get()` calls `get_json()` (which fetches JSON), then passes the text to `pd.read_json()`. But when `output="text"`, it also calls `get_json()`. The data flow is `get() -> get_json() -> HTTP -> text -> pd.read_json()`.

**This is fine for correctness, but the double text-to-JSON-to-DataFrame conversion could be avoided by passing the parsed JSON directly. Is this worth optimizing?**

### Q9.2 — `sgs.get()` with `multi=False` returns `List[pd.DataFrame]` for multiple codes

When `multi=False`, the function returns a bare list of DataFrames. This is a different return type than the single-code case (which returns a single DataFrame).

**Is this API surface confusing? Should `multi=False` always return a list (even for single codes) for consistency?**

### Q9.3 — `_get_url_and_payload` accepts `None` for `start_date` but doesn't validate

If `start_date` is `None` and `end_date` is also `None`, the function creates a URL with no date parameters (fetching the full series). But if `start_date` is `None` and `end_date` is provided, `Date(None)` will raise a `TypeError`.

**Should this validate the date combination explicitly?**

### Q9.4 — SGS `valor` field is not cast to numeric

`_format_df` renames `valor` to the series name but doesn't convert it from string to numeric. The JSON returns `"valor": "5.1234"` as a string. `pd.read_json()` may or may not auto-convert this depending on the pandas version.

**Should there be an explicit `pd.to_numeric()` conversion for the value column?**

---

## 10. Async Implementation

### Q10.1 — Async and sync code are fully duplicated

Every async function is a near-copy of its sync counterpart. `_async_currency_id_list` duplicates `_currency_id_list`, `_async_get_valid_currency_list` duplicates `_get_valid_currency_list`, etc. This means every bug fix or feature must be applied twice.

**Should we consider a pattern to reduce duplication (e.g. a shared core that accepts a client, or `asyncio.to_thread` for the sync versions)?**

### Q10.2 — `ODataService.__init__` is synchronous — no async constructor

There's no way to instantiate `ODataService` (and thus any `BaseODataAPI` subclass) asynchronously. The constructor makes two blocking HTTP requests. Users who want fully async code must still call `Expectativas()` synchronously.

**Should there be an async factory method like `await Expectativas.create()`?**

### Q10.3 — No `anyio` or `pytest-anyio` in dependencies but tests use `@pytest.mark.anyio`

The async tests use `@pytest.mark.anyio` but the `pyproject.toml` test dependencies don't include `anyio` or `pytest-anyio`.

**How are these tests currently running? Is `anyio` a transitive dependency? Should it be explicit?**

---

## 11. Testing

### Q11.1 — Integration test `test_currency_get_symbol` expects `_get_symbol("ZAR")` to return `None`

In `tests/integration/test_currency.py:27`, the test asserts `x = currency._get_symbol("ZAR", ...) ; assert x is None`. But the current code raises `CurrencyNotFoundError` instead of returning `None`.

**Is this integration test outdated / broken?**

### Q11.2 — `test_if_all_regions_and_states_are_there` checks `item.values()` instead of `item.keys()`

In `tests/sgs/test_regional_economy.py:66-68`, the test checks `list(item.values()) == list(BRAZILIAN_REGIONS.keys())`. This compares SGS *codes* (like `"15888"`) against region *keys* (like `"N"`), which will never match.

**Is this test incorrect, or am I misreading the assertion?**

### Q11.3 — No tests for `Endpoint.async_get()` with filters

The async OData tests only test basic `limit(1).async_collect()` and `async_get(limit=1)`. There are no tests for async queries with filters, orderby, or select.

**Should async query building be tested as thoroughly as the sync path?**

### Q11.4 — `tests/test_expectativas.py` is a stub redirecting to integration tests

The file just contains a comment: `# Tests moved to tests/integration/test_expectativas.py`. This is a dead file.

**Should it be deleted?**

### Q11.5 — `httpx_mock` Content-Type defaults may mask bugs

In some test mocks, `Content-Type` is not explicitly set (e.g. `add_currency_list_mock`). The default Content-Type from `pytest-httpx` may differ from what the real BCB API returns.

**Should all mocks explicitly set Content-Type to match production?**

### Q11.6 — No tests for `_get_valid_currency_list` rollback behavior

There are no unit tests for the date-rollback logic when the CSV file doesn't exist for a given date (weekends/holidays).

**Should the rollback logic be tested with mocked 404 responses?**

---

## 12. Project Structure & Packaging

### Q12.1 — `build/` directory contains stale legacy code

`build/lib/bcb/` contains old files (`series.py`, `sgs.py`) that don't exist in the current source tree. This directory is in `.gitignore` but `git status` shows it's not tracked.

**Should `build/` be cleaned up (it may confuse IDEs and tooling)?**

### Q12.2 — `pyproject.toml` has empty `description`

`description = ""` in `[project]`. PyPI shows this as empty.

**Should a proper description be added?**

### Q12.3 — No `py.typed` marker file

The package has full type annotations and passes `mypy --strict`, but there's no `py.typed` marker file. This means downstream consumers using mypy won't get type checking for `bcb` imports.

**Should `bcb/py.typed` be added?**

### Q12.4 — `numpy` is used in currency but not in dependencies

`bcb/currency.py` imports `numpy as np` (line 13) and uses `np.float64` (line 469). However, `numpy` is not in `[project.dependencies]` — it's presumably a transitive dependency of `pandas`.

**Should `numpy` be added to explicit dependencies, or should `np.float64` be replaced with `float`?**

### Q12.5 — No `__all__` exports in any module

None of the public modules define `__all__`. This means `from bcb import *` pulls in everything, and tools like `pyright` / `pylance` can't determine the public API.

**Should `__all__` be defined in `bcb/__init__.py` and the submodules?**

### Q12.6 — `BCBAPINotFoundError`, `BCBRateLimitError`, `BCBAPIServerError` not re-exported from `bcb/__init__.py`

The `__init__.py` exports `BCBError`, `BCBAPIError`, `CurrencyNotFoundError`, `SGSError`, `ODataError` but not the three newer subclasses.

**Should these be added to the top-level exports for user convenience?**

---

## 13. Performance

### Q13.1 — `currency.get()` fetches symbols sequentially

When fetching multiple currency symbols, the sync `get()` loops through symbols one at a time. Each symbol requires up to 3 HTTP requests (id list, currency list, rate data).

**Should we use `concurrent.futures.ThreadPoolExecutor` for parallel fetching in the sync API?**

### Q13.2 — `sgs.get()` fetches codes sequentially

Same issue — multiple SGS codes are fetched one at a time in the sync version.

**Same question: concurrent fetching for the sync path?**

### Q13.3 — `ODataMetadata._load_document()` parses full XML even if cached

The metadata is cached at the `ODataMetadata` level, but the `ODataService.__init__` still makes an HTTP call to the service root on every instantiation.

**Should the service root response also be cached?**

### Q13.4 — `pd.merge()` in `_get_currency_id` is O(n) per symbol

For each symbol lookup, the entire currency ID list and master list are merged. With many symbols, this repeats the same merge.

**Should the merge result be cached after the first call?**

---

## 14. Security

### Q14.1 — HTML parsing with `lxml` on untrusted input

`bcb/currency.py` uses `lxml.html.parse()` on responses from BCB. While BCB is a trusted source, if a MITM attack or DNS hijack occurs, the library would parse arbitrary HTML.

**Should `lxml` be configured with restricted parsing options, or is this an acceptable risk?**

### Q14.2 — No TLS certificate pinning

All HTTP requests go to `*.bcb.gov.br` without certificate pinning. This is standard practice but worth noting for security-conscious users.

**Is this acceptable, or should there be an option for custom CA bundles?**

### Q14.3 — OData query parameters are URL-encoded but not sanitized for injection

`ODataPropertyFilter.statement()` directly interpolates user-provided values into OData filter strings (e.g. `f"{self.obj.name} {self.operator} '{str(self.other)}'"`. A value containing a single quote could break the filter syntax.

**Should filter values be escaped/validated to prevent OData injection?**

---

## 15. Documentation

### Q15.1 — Mixed Portuguese and English in docstrings

Some docstrings are in Portuguese (e.g. `currency.get()`, `regional_economy`), others in English (e.g. `http.py`, `exceptions.py`). The README and CHANGELOG are in Portuguese.

**Should the codebase standardize on one language for docstrings?**

### Q15.2 — `currency.get()` docstring says `end` is "Data de *início*"

Line 615 says `end : ... Data de início da série` — should be "Data final".

**Typo to fix.**

### Q15.3 — `Date` accepts `int` per docstring but code doesn't handle it

The `sgs.get()` docstring says `start : str, int, date, datetime, Timestamp`, but `Date.__init__` doesn't handle `int`.

**Should `Date` handle integer timestamps, or should the docstring be corrected?**

### Q15.4 — No API reference in Sphinx docs for async functions

The `docs/async.rst` documents usage but the auto-generated API reference may not include the async functions.

**Should async functions be documented in the Sphinx API reference?**

---

## 16. Miscellaneous

### Q16.1 — `BRAZILIAN_STATES` is built with a module-level loop

`bcb/utils.py:13-15` uses a for-loop to build `BRAZILIAN_STATES` from `BRAZILIAN_REGIONS`. This works but is unusual for a constant.

**Should this be a list comprehension or tuple for clarity? Also, should it be a `tuple` (immutable) since it's a constant?**

### Q16.2 — `_CacheKey` has only a `type` field

`_CacheKey` is a `NamedTuple` with a single field `type`. It could just be a plain string.

**Is the NamedTuple adding value here, or is it over-engineered?**

### Q16.3 — `Endpoint.query()` and `Endpoint.async_query()` return the same thing

Both methods return `EndpointQuery(self._entity, self._url, self._date_columns)` — they're identical.

**Should `async_query()` be removed and users just use `query()` for both sync and async paths?**

### Q16.4 — No `__version__` attribute on the package

There's no way to check `bcb.__version__` at runtime. The version is only in `pyproject.toml`.

**Should `bcb/__init__.py` expose a `__version__` attribute (via `importlib.metadata` or similar)?**

### Q16.5 — `conftest.py` `make_currency_rate_csv` uses period (`.`) as decimal separator in f-string

The function generates CSV like `{bid:.4f}` which uses `.` (period) as decimal separator. But the actual BCB CSV uses `,` (comma) as decimal separator. The `_parse_currency_types` function does `str.replace(",", ".")` before converting to float.

**Are the test fixtures accurately representing the real CSV format? The mock CSV uses periods, while the real API uses commas.**

### Q16.6 — `asyncio` is imported in `currency.py` but only used by async functions

The `asyncio` import at the top of `currency.py` is only needed for the async functions at the bottom of the file.

**Should the import be inside the async functions, or is top-level fine?**

---

## Summary

| Category | Count |
|---|---|
| HTTP Client Lifecycle | 3 |
| Retry & Resilience | 4 |
| Error Handling | 8 |
| Caching | 4 |
| Date Utility | 3 |
| Type Safety & API Design | 6 |
| OData Framework | 8 |
| Currency Module | 6 |
| SGS Module | 4 |
| Async Implementation | 3 |
| Testing | 6 |
| Project Structure | 6 |
| Performance | 4 |
| Security | 3 |
| Documentation | 4 |
| Miscellaneous | 6 |
| **Total** | **78** |
