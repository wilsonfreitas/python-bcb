# Plan: python-bcb Improvements (QUESTIONS.md)

## Context
50 architectural/design questions were raised in a code review of python-bcb (Brazilian Central Bank API client). The user reviewed and answered all questions. This plan organizes the actionable decisions into 8 independent implementation phases, ordered by dependency.

---

## Architecture Decisions (Finalized)

| # | Decision |
|---|----------|
| A1 | **Shared global `httpx.Client`** in `bcb/http.py`, imported by all modules |
| A2 | **Fail-fast everywhere**: `_fetch_symbol_response` raises immediately; `get(["USD", "BOGUS"])` raises `CurrencyNotFoundError` on first invalid symbol |
| A3 | **True async via `httpx.AsyncClient`**: add `async_get()` functions in each module |
| A4 | **Format detection**: assert expected response structure, raise descriptive `BCBAPIError` if BCB API format changes |

---

## Phase 1: Shared HTTP Infrastructure
**Dependencies:** None — must be done first (all other phases depend on it)

**Files to create/modify:**
- `bcb/http.py` (NEW) — shared client module
- `bcb/currency.py`
- `bcb/sgs/__init__.py`
- `bcb/odata/framework.py`
- `pyproject.toml` — add `tenacity` dependency

**Changes:**
- Create `bcb/http.py` with:
  - `_CLIENT = httpx.Client(timeout=30.0, follow_redirects=True)` (sync)
  - `_ASYNC_CLIENT = httpx.AsyncClient(timeout=30.0, follow_redirects=True)` (async)
  - `DEFAULT_TIMEOUT = 30.0` constant
- Replace all bare `httpx.get()` calls across modules with `_CLIENT.get()`
- Standardize timeout: all calls use `DEFAULT_TIMEOUT`, allow per-call override via `timeout=` kwarg
- Add `tenacity`-based `@retry` decorator for transient network errors (max 3 retries, fixed wait)
- Fix `_get_valid_currency_list` recursive date-rollback: add `max_rollback=30` depth guard to prevent `RecursionError`
- Fix `http://` URL in `_get_valid_currency_list` → `https://`

**No async API yet** — `_ASYNC_CLIENT` just defined, used in Phase 6.

---

## Phase 2: Exception Hierarchy & Error Handling
**Dependencies:** Phase 1 (HTTP client standardized)

**Files:**
- `bcb/exceptions.py`
- `bcb/currency.py`
- `bcb/sgs/__init__.py`

**Changes:**
- In `bcb/exceptions.py`:
  - Make `BCBAPIError.status_code` required (remove `Optional`)
  - Add `BCBAPINotFoundError(BCBAPIError)` — for 404 responses
  - Add `BCBRateLimitError(BCBAPIError)` — for 429 responses
- In `bcb/currency.py`:
  - Remove `warnings.warn()` at L141 → raise `BCBAPIError` with status code
  - Change `_fetch_symbol_response` to raise (never return `None`) — per A2 decision
  - Remove `Optional` return type from `_fetch_symbol_response`, `_get_symbol`, `_get_symbol_text`
  - Detect 429 → raise `BCBRateLimitError`
  - Detect 404 → raise `BCBAPINotFoundError`
- In `bcb/sgs/__init__.py`:
  - Replace bare `except Exception` (L253) with `except json.JSONDecodeError`
  - Detect 429 → raise `BCBRateLimitError`

---

## Phase 3: Cache Refactor
**Dependencies:** None (independent)

**Files:**
- `bcb/currency.py`
- `bcb/odata/framework.py`

**Changes:**
- In `bcb/currency.py`:
  - Replace `_CACHE: dict[str, pd.DataFrame]` with a thread-safe wrapper class:
    ```python
    class _Cache:
        def __init__(self) -> None:
            self._lock = threading.Lock()
            self._data: dict[CacheKey, pd.DataFrame] = {}
        def get(self, key): ...
        def set(self, key, value): ...
        def clear(self): ...
    ```
  - Replace string keys `"TEMP_CURRENCY_ID_LIST"` / `"TEMP_FILE_CURRENCY_LIST"` with a `CacheKey` namedtuple (or `@dataclass(frozen=True)`)
  - Make cache injectable: `get(..., cache: _Cache = _DEFAULT_CACHE)` — module-level default, but testable
  - Update `clear_cache()` to delegate to `_DEFAULT_CACHE.clear()`
- In `bcb/odata/framework.py`:
  - Add module-level `_METADATA_CACHE: dict[str, ODataMetadata] = {}` (keyed by URL)
  - In `ODataService.__init__`: check cache before fetching `$metadata`
  - Cache is in-memory, no TTL, lives with process

---

## Phase 4: Data Validation & Type Safety
**Dependencies:** Phases 1 and 2 (exception classes must exist)

**Files:**
- `bcb/currency.py`
- `bcb/sgs/__init__.py`
- `bcb/odata/api.py`
- `bcb/odata/framework.py`
- `bcb/utils.py`

**Changes:**
- **CSV validation** (`bcb/currency.py`):
  - Assert CSV has exactly 8 columns after parsing; raise `BCBAPIError` if not
  - Add explicit `errors='raise'` to `.astype()` calls for type conversion failures
- **Date validation** (`bcb/currency.py`, `bcb/sgs/__init__.py`):
  - Wrap `pd.to_datetime(..., format=...)` in try/except `ValueError` → raise `BCBAPIError` with descriptive message
- **Type conversion validation** (`bcb/currency.py`):
  - Wrap `.astype("int32")` and `.astype(np.float64)` conversions in try/except → raise `BCBAPIError`
- **SGSCode → dataclass** (`bcb/sgs/__init__.py`):
  - Convert `SGSCode` to `@dataclass`:
    ```python
    @dataclass(frozen=True)
    class SGSCode:
        value: int
        name: str

        @classmethod
        def from_code(cls, code: int | str) -> SGSCode: ...

        @classmethod
        def from_named(cls, code: int | str, name: str) -> SGSCode: ...

        def __repr__(self) -> str: ...
    ```
  - Remove the always-true nested `if isinstance(code, int | str)` check
- **SGS input validation** (`bcb/sgs/__init__.py`):
  - In `_codes()`: validate that int codes are positive; raise `ValueError` if not
- **TypedDict for dict returns** (`bcb/currency.py`, `bcb/sgs/__init__.py`):
  - Define `CurrencyTextResult = TypedDict("CurrencyTextResult", {"symbol": str, ...})`
  - Update overload declarations to use `TypedDict`
- **Absolute imports + annotations** (all `bcb/` files):
  - Add `from __future__ import annotations` to every file
  - Convert all relative imports to absolute imports (e.g., `from .exceptions` → `from bcb.exceptions`)
- **Format detection** (`bcb/currency.py`, `bcb/sgs/__init__.py`, `bcb/odata/framework.py`):
  - Add `_validate_*_response()` helpers that assert expected response structure
  - Called immediately after HTTP response parsing

---

## Phase 5: API Consistency
**Dependencies:** Phases 1–4

**Files:**
- `bcb/currency.py`
- `bcb/sgs/__init__.py`
- `bcb/odata/api.py`
- `bcb/odata/framework.py`

**Files to change:**
- `bcb/currency.py` — URL construction fix only
- `bcb/odata/api.py` — Endpoint.get() explicit kwargs
- `bcb/sgs/__init__.py` — no URL changes needed (payload dict already passed via `params=` to httpx)

**Changes:**

**5A: `bcb/currency.py` — `_currency_url()` uses urlencode**

Add `from urllib.parse import urlencode` and replace inline f-string query params:

```python
def _currency_url(currency_id: int, start_date: DateInput, end_date: DateInput) -> str:
    start_date = Date(start_date)
    end_date = Date(end_date)
    params = urlencode({
        "method": "gerarCSVFechamentoMoedaNoPeriodo",
        "ChkMoeda": currency_id,
        "DATAINI": start_date.date.strftime("%d/%m/%Y"),
        "DATAFIM": end_date.date.strftime("%d/%m/%Y"),
    })
    return f"https://ptax.bcb.gov.br/ptax_internet/consultaBoletim.do?{params}"
```

**5B: `bcb/odata/api.py` — explicit kwargs on `Endpoint.get()`**

Add typed explicit kwargs while keeping `*args` for backwards compatibility:

```python
def get(
    self,
    *args: Any,
    filter: Optional[ODataPropertyFilter] = None,
    orderby: Optional[ODataPropertyOrderBy] = None,
    select: Optional[ODataProperty] = None,
    limit: Optional[int] = None,
    skip: Optional[int] = None,
    output: str = "dataframe",
    **kwargs: Any,
) -> Union[pd.DataFrame, str]:
```

Apply explicit kwargs first, then process `*args` positional dispatch.
`filter` shadows the built-in intentionally (common pattern in Python ORMs).

---

## Phase 6: Async API
**Dependencies:** Phase 1 (`_ASYNC_CLIENT` defined), Phases 2–5 (stable sync API)

**Files to change:**
- `bcb/sgs/__init__.py` — `async_get_json()` + `async_get()` with `asyncio.gather()`
- `bcb/currency.py` — full async internal chain + `async_get()`
- `bcb/odata/framework.py` — `ODataQuery.async_text()` + `ODataQuery.async_collect()`
- `bcb/odata/api.py` — `EndpointQuery.async_collect()` + `Endpoint.async_get()` + `Endpoint.async_query()`

`bcb/http.py` needs no changes — `_ASYNC_CLIENT` already defined.

---

### 6A: `bcb/sgs/__init__.py`

Add `import asyncio` and `from bcb.http import _ASYNC_CLIENT` to imports.

```python
async def async_get_json(code, start=None, end=None, last=0) -> str:
    url, payload = _get_url_and_payload(code, start, end, last)
    res = await _ASYNC_CLIENT.get(url, params=payload)
    if res.status_code == 429:
        raise BCBRateLimitError(...)
    if res.status_code != 200:
        try:
            res_json = json.loads(res.text)
        except json.JSONDecodeError:
            res_json = {}
        if "error" in res_json:
            raise SGSError(f"BCB error: {res_json['error']}")
        elif "erro" in res_json:
            raise SGSError(f"BCB error: {res_json['erro']['detail']}")
        raise SGSError(f"Download error: code = {code}")
    return str(res.text)


async def async_get(codes, start=None, end=None, last=0, multi=True, freq=None, output="dataframe"):
    code_list = list(_codes(codes))
    # Concurrent HTTP requests via asyncio.gather()
    texts = await asyncio.gather(
        *[async_get_json(c.value, start, end, last) for c in code_list]
    )
    if output == "text":
        results = {c.value: t for c, t in zip(code_list, texts)}
        if len(results) == 1:
            return next(iter(results.values()))
        return results
    dfs = [_format_df(pd.read_json(StringIO(t)), c, freq) for c, t in zip(code_list, texts)]
    if len(dfs) == 1:
        return dfs[0]
    return pd.concat(dfs, axis=1) if multi else dfs
```

---

### 6B: `bcb/currency.py`

Add `import asyncio` and `from bcb.http import _ASYNC_CLIENT` to imports.

Write async versions of the internal chain — all sharing the same `_DEFAULT_CACHE`
(the `threading.RLock()` is safe to acquire briefly from async code since cache
operations are O(1) dict lookups):

```python
async def _async_currency_id_list(cache=None) -> pd.DataFrame:
    # Check cache; fetch HTML via _ASYNC_CLIENT if miss; same parse logic as sync

async def _async_get_valid_currency_list(_date, n=0, max_rollback=30):
    # Same date rollback loop as sync, but with await _ASYNC_CLIENT.get()

async def _async_get_currency_list(cache=None) -> pd.DataFrame:
    # Check cache; call _async_get_valid_currency_list() if miss; same parse

async def _async_get_currency_id(symbol) -> int:
    # Concurrent: asyncio.gather(_async_currency_id_list(), _async_get_currency_list())
    # Then same merge/lookup logic as _get_currency_id()

async def _async_fetch_symbol_response(symbol, start_date, end_date):
    # cid = await _async_get_currency_id(symbol)
    # res = await _ASYNC_CLIENT.get(_currency_url(cid, start_date, end_date))
    # Same HTML error page check + HTTP status checks as sync version

async def _async_get_symbol(symbol, start_date, end_date) -> pd.DataFrame:
    # res = await _async_fetch_symbol_response(...)
    # Then same _validate_currency_csv / _parse_currency_dates / _parse_currency_types pipeline

async def _async_get_symbol_text(symbol, start_date, end_date) -> str:
    # res = await _async_fetch_symbol_response(...)
    # return res.text

async def async_get(symbols, start, end, side="ask", groupby="symbol", output="dataframe"):
    # Concurrent requests: asyncio.gather(*[_async_get_symbol(s,...) for s in symbols])
    # Same side/groupby post-processing as sync get()
```

---

### 6C: `bcb/odata/framework.py`

Add `from bcb.http import _ASYNC_CLIENT` to imports.
Add two methods to `ODataQuery`:

```python
async def async_text(self) -> str:
    # Identical query-string building to text() (reuse _build_parameters())
    # Only difference: await _ASYNC_CLIENT.get(...) instead of _CLIENT.get(...)

async def async_collect(self) -> Any:
    return json.loads(await self.async_text())
```

---

### 6D: `bcb/odata/api.py`

Add `import asyncio` to imports.

`EndpointQuery`:
```python
async def async_collect(self, output="dataframe") -> Union[pd.DataFrame, str]:
    if output == "text":
        return await self.async_text()
    raw_data = await super().async_collect()
    data = pd.DataFrame(raw_data["value"])
    # Same date-column logic as sync collect()
    return data
```

`Endpoint`:
```python
def async_query(self) -> EndpointQuery:
    return EndpointQuery(self._entity, self._url, self._date_columns)

async def async_get(self, *args, filter=None, orderby=None, select=None,
                    limit=None, skip=None, output="dataframe", verbose=False, **kwargs):
    # Same query setup as sync get(), but final call uses:
    # await _query.async_collect(output="text") or await _query.async_collect()
```

---

### Lifecycle note

Document in `bcb/http.py` docstring and `close_async_client()` that the
`_ASYNC_CLIENT` module-level singleton should be closed in long-running apps:

```python
await bcb.http.close_async_client()  # or via asyncio context manager
```

---

## Phase 7: Testing Overhaul
**Dependencies:** Phases 1–5 complete (stable API)

**Files:**
- `tests/conftest.py`
- `tests/test_currency.py`
- `tests/test_sgs.py`
- `tests/test_odata.py` (new)
- `tests/integration/` (existing)

**Changes:**
- Replace hardcoded mock data constants in `conftest.py` with factory functions
  - e.g., `make_currency_csv(symbols=["USD"], dates=1)` generates minimal valid CSV
  - e.g., `make_sgs_response(code=1, n=1)` generates minimal valid JSON
- Add comprehensive negative test cases:
  - Malformed input: bad dates, invalid symbols, non-integer SGS codes, empty symbol list
  - API failures: 404, 429, 500 responses
  - Network failures: connection timeout, malformed JSON, malformed CSV, wrong column count
- Use `pytest-httpx` to mock all HTTP calls in unit tests (eliminate all flakiness)
- Move all tests using live HTTP to `tests/integration/`
- Remove `@mark.flaky` from any test where HTTP is now properly mocked
- Add tests for thread-safety of cache (concurrent reads/writes)
- Add tests for async API (use `pytest-anyio` or `anyio`)

---

## Phase 8: Logging & Documentation
**Dependencies:** All previous phases (API surface is stable)

**Files:**
- All `bcb/` modules
- `README.md`
- `docs/` (existing Sphinx docs)
- `examples/` (NEW directory)

**Changes:**
- **Logging** (`bcb/currency.py`, `bcb/sgs/__init__.py`, `bcb/odata/framework.py`):
  - Add `logger = logging.getLogger(__name__)` to each module
  - `logger.debug()` before each HTTP request: URL and params (no secrets)
  - `logger.debug()` after each response: status code and content length
  - `logger.warning()` for retry attempts
- **Docstrings** (all public functions):
  - Full docstrings: summary, Parameters, Returns, Raises sections
  - Minimal one-line docstrings for private helpers
  - Add `pydocstyle` to ruff config (or `ruff` rule `D` subset)
- **Examples** (`examples/`):
  - `examples/sgs_time_series.py` — basic SGS usage
  - `examples/currency_exchange.py` — currency rate fetching
  - `examples/odata_query.py` — OData filter/orderby usage
  - `examples/async_usage.py` — async API example
- **README** (`README.md`):
  - Add "Which module to use?" decision table
  - Add FAQ section for common use cases

---

## Summary

| Phase | Area | Key Files | Scope |
|-------|------|-----------|-------|
| 1 | Shared HTTP client | `bcb/http.py` (new), 3 existing | Foundation |
| 2 | Exception hierarchy | `bcb/exceptions.py`, `bcb/currency.py`, `bcb/sgs/__init__.py` | Errors |
| 3 | Cache refactor | `bcb/currency.py`, `bcb/odata/framework.py` | State mgmt |
| 4 | Data validation & types | 5 files | Type safety |
| 5 | API consistency | 4 files | API polish |
| 6 | Async API | 5 files | New feature |
| 7 | Testing overhaul | `tests/` | Quality |
| 8 | Logging & docs | All + new `examples/` | DX |

## Verification (Run After Each Phase)
```bash
uv run pytest -m "not integration"
uv run ruff check bcb/ tests/
uv run ruff format --check bcb/ tests/
uv run mypy bcb/
```
