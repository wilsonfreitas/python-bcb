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

**Changes:**
- **Standardize `start`/`end` parameter names** across all modules (already consistent; verify and document)
- **URL construction** (`bcb/currency.py`, `bcb/sgs/__init__.py`):
  - Replace raw f-string URL building with `urllib.parse.urlencode` / `urllib.parse.urljoin` where user input is involved
  - Note: OData framework already uses `urllib.parse.quote` — leave as-is
- **OData `.get()` keyword args** (`bcb/odata/api.py`):
  - Add `filter=`, `orderby=`, `select=` as explicit keyword args to `Endpoint.get()` in addition to existing positional args

---

## Phase 6: Async API
**Dependencies:** Phase 1 (`_ASYNC_CLIENT` defined), Phases 2–5 (stable sync API)

**Files:**
- `bcb/sgs/__init__.py`
- `bcb/currency.py`
- `bcb/odata/framework.py`
- `bcb/odata/api.py`
- `bcb/http.py`

**Changes:**
- Add `async_get()` in `bcb/sgs/__init__.py`:
  - Same signature as `get()` but `async def async_get(...)`
  - Uses `_ASYNC_CLIENT.get()` from `bcb/http.py`
  - Internal `_async_get_json()` helper
- Add `async_get()` in `bcb/currency.py`:
  - Async version of the currency fetch flow
- Add `async_text()` / `async_collect()` to `ODataQuery` in `bcb/odata/framework.py`
- Add `async_get()` / `async_query()` to `Endpoint` in `bcb/odata/api.py`
- Lifecycle note: `_ASYNC_CLIENT` is a module-level object; document that it should be closed in long-running apps via `bcb.http.close_async_client()`

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
