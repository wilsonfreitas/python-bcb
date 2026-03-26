# python-bcb Code Review Questions

This document contains architectural, technical, refactoring, and design questions identified during a comprehensive code review. These are organized by category to help you systematically address them.

---

## HTTP Client & Connection Management

### Q1: HTTP Connection Pooling & Reuse
**What:** The code uses `httpx.get()` repeatedly throughout, but there's no explicit connection pooling or client reuse. Each `httpx.get()` call may create/close connections.

**Why it matters:** Performance and resource efficiency, especially for long-running applications or when making many requests.

**Affected code:**
- `bcb/currency.py`: Lines 53, 70, 132, 273
- `bcb/sgs/__init__.py`: Line 249
- `bcb/odata/framework.py`: Lines 273, 357, 512

**Questions:**
- Should we use a session-based `httpx.Client()` instance to maintain connection pooling?
    - What are the benefits of using connection pooling?
    - Can I use connection pooling for different URLs on the same server?
- If so, how should lifecycle (initialization/cleanup) be managed?
    - Bring me examples.
- Should different modules share the same client or have separate ones?
    - Different modules use different URLs, can I use different URLs in the same client?

---

### Q2: Timeout Configuration & Consistency
**What:** Some HTTP calls use explicit timeout (60.0s), others rely on default.

**Why it matters:** Prevents indefinite hangs, but inconsistent timeouts may cause unexpected failures.

**Affected code:**
- `bcb/odata/framework.py` L273, L357, L512 have explicit `timeout=60.0`
- `bcb/currency.py` and `bcb/sgs/__init__.py` have no explicit timeout

**Questions:**
- Should all HTTP calls have a consistent timeout strategy?
    - Yes, they should, to be consistent.
- Should timeout be configurable globally or per-call?
    - It should have a default value and allow a configuration per-call.
- What's the appropriate timeout for different APIs (currency, SGS, OData)?
    - I don´t know.

---

### Q3: Retry Logic & Exponential Backoff
**What:** `_get_valid_currency_list()` implements manual retry with simple recursion. No exponential backoff or circuit breaker pattern.

**Why it matters:** Resilience to transient failures, but current implementation may hammer the API if it's truly down.

**Affected code:**
- `bcb/currency.py` L67–78

**Questions:**
- Should retry logic be standardized across all modules?
    - Yes, it should.
- Should we use a library like `tenacity` or `backoff` for more sophisticated retry strategies?
    - Yes, we should.
- Is exponential backoff with jitter needed?
    - No, it is not.
- Should there be a maximum retry count or total timeout?
    - Yes, there should be a maximum retry count. It also can have a default value and be passed as an argument.

---

### Q4: Error Response Handling Inconsistency
**What:** Some endpoints check `res.status_code == 200`, others check `!= 200`. Some raise exceptions, others return `None` or warnings.

**Why it matters:** Inconsistent error handling makes the API harder to use and may mask failures.

**Affected code:**
- `bcb/currency.py` L54–56 (raises `BCBAPIError`)
- `bcb/currency.py` L133–142 (issues `warnings.warn()` and returns `None`)
- `bcb/sgs/__init__.py` L250–259 (raises `SGSError`)

**Questions:**
- Should all errors be raised as exceptions (fail-fast) or should some return `None`?
    - All errors should be raised as exceptions.
- Should warnings be replaced with exceptions or logging?
    - Yes, warnings should be replaced with exceptions.
- What's the intended behavior when an API returns a non-200 status?
    - Show that request has failed.

---

## Caching & State Management

### Q5: Module-Level Mutable Global State
**What:** `bcb/currency.py` uses a module-level `_CACHE` dictionary (line 30). This is shared across all imports and threads.

**Why it matters:** Thread-safety issues, difficult to debug, potential memory leaks, and testing complications.

**Affected code:**
- `bcb/currency.py` L30, L46–48, L91–92, L110

**Questions:**
- Is thread-safety a concern for this library? Should cache be thread-safe?
    - Yes, absolutely.
- Should cache be moved to an injectable dependency instead of a global?
    - Yes, absolutely.
- Should cache behavior be configurable (disable, TTL, max size)?
    - No, it should not.

---

### Q6: Cache Invalidation Strategy
**What:** Cache never expires. The only way to invalidate is calling `clear_cache()` explicitly.

**Why it matters:** Stale data may be served in long-running applications.

**Affected code:**
- `bcb/currency.py` L30–43

**Questions:**
- Should cache entries have a TTL (time-to-live)?
    - No, it should not.
- Should currency list be refreshed periodically (e.g., daily) even without explicit clearing?
    - No, it should not.
- Should cache size be bounded? (e.g., LRU cache with max entries)
    - No, it should not.
- Should different data types have different cache policies?
    - No, it should not.

---

### Q7: Cache Key Collisions
**What:** Cache uses string keys like `"TEMP_CURRENCY_ID_LIST"` and `"TEMP_FILE_CURRENCY_LIST"` without namespacing.

**Why it matters:** Future changes could accidentally overwrite cache entries. Prefix `TEMP_` is unclear.

**Affected code:**
- `bcb/currency.py` L46, L63, L91, L110

**Questions:**
- Why the `TEMP_` prefix? What does it signify?
    - Probably it is a legacy.
- Should we use a more structured cache key system (e.g., dataclass or namedtuple)?
    - Yes, we use since it makes the code more robust.
- Could cache be organized hierarchically (e.g., `{"currency_id_list": {...}, "currency_list": {...}}`)?
    - No, it could not.

---

### Q8: OData Metadata Caching
**What:** `ODataService` fetches and parses metadata on every instantiation. No explicit caching of metadata.

**Why it matters:** Performance. Metadata rarely changes, but it's fetched every time an API instance is created.

**Affected code:**
- `bcb/odata/framework.py` L354–363

**Questions:**
- Should metadata be cached (e.g., on disk or in memory) between instances?
    - Yes, absolutely, in memory.
- Should there be an option to use cached metadata vs. fresh metadata?
    - No, there should not.
- How would cache invalidation work for OData metadata?
    - Once it is in memory, it lives as long as the application lives.

---

## Error Handling & Exceptions

### Q9: Bare Exception Handling
**What:** `bcb/sgs/__init__.py` L253 catches bare `Exception` which could hide unexpected errors.

**Why it matters:** Makes debugging harder; could mask programming errors.

**Affected code:**
- `bcb/sgs/__init__.py` L251–254

**Questions:**
- Why is a bare `Exception` caught? What specific exceptions are expected?
    - I don´t know.
- Should this be more specific (e.g., `json.JSONDecodeError`)?
    - Yes, this should.
- Is there a fallback strategy if JSON parsing fails?
    - No, there is not.

---

### Q10: None Return vs. Exception Raising
**What:** Some functions raise exceptions on error, others return `None`.

**Why it matters:** Inconsistent API; callers must handle different patterns. `None` can be accidentally used without checking.

**Affected code:**
- `bcb/currency.py` L126 (`_fetch_symbol_response` returns `Optional[httpx.Response]`)
- `bcb/currency.py` L148 (`_get_symbol` returns `Optional[pd.DataFrame]`)
- `bcb/currency.py` L171 (`_get_symbol_text` returns `Optional[str]`)

**Questions:**
- Should all public/private functions follow the same error strategy?
    - Yes, public API should, private API not 100%. For private API we should create a naming structure to accomodate the expected behavior.
- Is returning `None` preferable to raising for "data not found" vs. "API error"?
    - I believe returning 'None' is preferable, but I am not 100% sure.
- Should we use `Result[T, E]` or `Optional[T]` types consistently?
    - Yes, we should, that would be awesome.

---

### Q11: Warning vs. Exception for API Errors
**What:** `bcb/currency.py` L141 issues a warning for API errors and returns `None` instead of raising.

**Why it matters:** Callers may not see the warning. Downstream errors will be harder to trace.

**Affected code:**
- `bcb/currency.py` L133–142

**Questions:**
- Why does this case use `warnings.warn()` instead of raising `CurrencyNotFoundError`?
    - I don´t know.
- Should this be an exception? If not, how should the caller detect this error?
    - Yes, this should.

---

### Q12: BCBAPIError Status Code Handling
**What:** `BCBAPIError` optionally stores `status_code`, but not all places pass it when raising.

**Why it matters:** Callers trying to differentiate errors by status code may get `None`.

**Affected code:**
- `bcb/exceptions.py` L5–10
- `bcb/currency.py` L56

**Questions:**
- Should `status_code` be required or optional?
    - It should be required, but we also should understand the details.
- Should there be specialized subclasses (e.g., `BCBAPINotFoundError` for 404)?
    - Yes, there should.
- Should we raise on specific status codes (401, 403, 429) with different logic?
    - No, we should not.
---

## Data Parsing & Validation

### Q13: Magic Column Names in CSV Parsing
**What:** `bcb/currency.py` L152 defines columns as `["Date", "aa", "bb", "cc", "bid", "ask", "dd", "ee"]`. The "aa", "bb", etc. are mysterious.

**Why it matters:** Unclear intent. Fragile if CSV format changes. Hard to maintain.

**Affected code:**
- `bcb/currency.py` L152–163

**Questions:**
- What do columns "aa", "bb", "cc", "dd", "ee" represent?
    - These columns should be ignored.
- Are they always 8 columns? What if the format changes?
    - It won´t change.
- Should these be constants with meaningful names?
    - No, they should not.
- Should we validate that the CSV has exactly 8 columns?
    - Yes, we should.

---

### Q14: Date Format Assumptions
**What:** Multiple hardcoded date formats throughout code. No validation that date parsing succeeds.

**Why it matters:** If BCB API changes format, silent failures could occur.

**Affected code:**
- `bcb/currency.py` L157 (`format="%d%m%Y"`)
- `bcb/sgs/__init__.py` L96 (`format="%d/%m/%Y"`)
- `bcb/odata/api.py` L34, L78 (endpoint-specific overrides)

**Questions:**
- Should date format be configurable?
    - No, it should not.
- Should we validate that date parsing succeeds and raise on malformed dates?
    - Yes, we should.
- Should regional_economy.py L148 raise a more informative error if location is invalid?
    - No, it should not.

---

### Q15: Implicit Type Conversions in Data Processing
**What:** Many implicit conversions: string → int, float with comma → float, etc.

**Why it matters:** Silent failures if data is malformed.

**Affected code:**
- `bcb/currency.py` L62 (`.astype("int32")`)
- `bcb/currency.py` L107–108 (`.astype("int32")`)
- `bcb/currency.py` L158–159 (string replace + `.astype(np.float64)`)

**Questions:**
- Should we validate data types before conversion?
    - Yes, we should.
- Should conversion failures be raised explicitly?
    - Yes, we should.
- Should there be a data validation step that warns about malformed records?
    - Yes, there should.

---

### Q16: Regional Economy Exception Handling
**What:** `bcb/sgs/regional_economy.py` L148 raises generic `Exception` with a string message.

**Why it matters:** Not a custom exception; harder to catch and handle programmatically.

**Affected code:**
- `bcb/sgs/regional_economy.py` L148

**Questions:**
- Should this raise a custom exception like `InvalidRegionError` or `InvalidStateError`?
    - No, it should not.
- Should the error message be more detailed (e.g., list valid regions/states)?
    - No, it should not.

---

## Type Safety & Annotations

### Q17: Complex Metaclass Type Assignments
**What:** `bcb/odata/api.py` uses metaclasses to dynamically set attributes on instances (lines 21–29, 23–28).

**Why it matters:** Type checkers may not understand dynamic attributes. Runtime errors if assumptions are wrong.

**Affected code:**
- `bcb/odata/api.py` L16–29 (`EndpointMeta`)
- `bcb/odata/framework.py` L56–65 (`ODataEntitySetMeta`)

**Questions:**
- Is the metaclass complexity necessary?
    - Yes, it is.
- Could we use `__getattr__` instead of dynamically setting attributes?
    - Yes, we could use that but once I know what to set it is not necessary.
- Should we use `@property` methods or a `__getattribute__` override?
    - No, we should not.
- How does type checking handle these dynamic attributes?
    - It doesn't handle, but it could.

---

### Q18: Type Annotations for Dictionary Returns
**What:** Some functions return `Dict[str, str]` but could be more specific about the keys/values.

**Why it matters:** Users can't know what keys to expect.

**Affected code:**
- `bcb/currency.py` L205 (returns `Union[pd.DataFrame, str, Dict[str, str]]`)
- `bcb/sgs/__init__.py` L137 (returns `Union[pd.DataFrame, List[pd.DataFrame], str, Dict[int, str]]`)

**Questions:**
- Should we use `TypedDict` for more specific dictionary types?
    - Yes, we should.
- Should we have separate return types for different `output` parameter values?
    - Yes, we should.
- Could we use overloads more extensively to make return types clearer?
    - Yes, we could.

---

### Q19: Union Types Overuse
**What:** Several `Union` types are very long, making signatures hard to read.

**Why it matters:** Harder to understand API contract. Users unsure what to expect.

**Affected code:**
- `bcb/sgs/__init__.py` L46–52 (`SGSCodeInput`)
- `bcb/odata/framework.py` L165–167 (`ODataPropertyFilter.__init__`)

**Questions:**
- Could some Union types be better expressed as Protocol or ABC?
    - Yes, they could.
- Could input validation normalize these types to a single canonical form?
    - Yes, it could.

---

## Code Quality & Documentation

### Q20: Portuguese/English Mixing
**What:** Docstrings and comments are mostly Portuguese; variable/function names are English.

**Why it matters:** Inconsistent and harder for non-Portuguese speakers to understand.

**Affected code:**
- Throughout `bcb/sgs/__init__.py`, `bcb/currency.py`, etc.

**Questions:**
- Should the codebase standardize on English or Portuguese?
    - The codebase is in English, but the docstrings in Portuguese.
- If English, should docstrings be translated?
    - The codebase is in English, but the docstrings in Portuguese.
- Should there be a convention for comments vs. docstrings?
    - No, there should not.

---

### Q21: Missing Docstrings
**What:** Some functions lack docstrings or have minimal documentation.

**Why it matters:** Users can't self-serve. IDE autocomplete lacks context.

**Affected code:**
- `bcb/odata/framework.py`: Many internal functions (e.g., `str_types`, `_parse_entity`)
- `bcb/utils.py`: Limited docstrings on `Date` class methods
- Private/internal functions generally lack docs

**Questions:**
- Should all public functions have full docstring (parameters, returns, raises)?
    - Yes, they should.
- Should internal functions be documented?
    - Yes, they should.
- Should we enforce docstring requirements in linting (e.g., `pydocstyle`)?
    - Yes, we should.

---

### Q22: Unclear Function Purposes
**What:** Some helper functions have unclear purposes (e.g., `_codes()` generator, `_format_df()`).

**Why it matters:** Code harder to understand. Harder to modify without breaking things.

**Affected code:**
- `bcb/sgs/__init__.py` L55–68 (`_codes()` generator)
- `bcb/sgs/__init__.py` L92–102 (`_format_df()`)
- `bcb/currency.py` L169–173 (`_get_symbol_text()`)

**Questions:**
- Should these helper functions have clearer names?
    No, it should not.
- Should they be documented with examples?
    No, they should not.
- Could they be refactored into a class/module for clarity?
    No, they could not.

---

## Architecture & API Consistency

### Q23: Inconsistent API Between Modules
**What:** Each module has different signatures and patterns:
- `sgs.get(codes, start, end, last, multi, freq, output)`
- `currency.get(symbols, start, end, side, groupby, output)`
- `odata.get_endpoint().get(*args, **kwargs)`

**Why it matters:** Users must learn different patterns. Hard to create generic utilities.

**Affected code:**
- `bcb/sgs/__init__.py` L129–205
- `bcb/currency.py` L198–277
- `bcb/odata/api.py` L120–166

**Questions:**
- Should all modules share a common interface?
    - No, it is not necessary.
- Should there be a unified `bcb.get()` function that dispatches to the right module?
    - Good idea, I'd love to hear more on that.
- Should parameter names be standardized (e.g., all use `start`/`end` or all use `from`/`to`)?
    - Yes, they should.

---

### Q24: ODataQuery vs. Endpoint.query()
**What:** Both `ODataQuery` and `Endpoint.query()` exist. Users can use either API. Unclear which is preferred.

**Why it matters:** Cognitive overload. Inconsistent documentation.

**Affected code:**
- `bcb/odata/api.py` L120–166 vs. L168–176

**Questions:**
- Should `Endpoint.get()` be the primary API and `query()` be secondary?
    - No, it is not necessary.
- Should `query()` return an `EndpointQuery` that chains to `.collect()`, or `.get()`?
    - No, it is not necessary.
- Should there be examples showing both patterns?
    - Yes, there should be more examples.

---

### Q25: `raw()` Parameter Inconsistency
**What:** Some modules have `output='text'` for raw data, but OData also has a `.raw()` method on queries.

**Why it matters:** Inconsistent API. Users unsure how to get raw data.

**Affected code:**
- `bcb/currency.py` L198–205 (output parameter)
- `bcb/sgs/__init__.py` L129–174 (output parameter)
- `bcb/odata/framework.py` L476–478 (`.raw()` method)

**Questions:**
- Should all modules use the same pattern for raw output (parameter vs. method)?
    - I like the idea, but how?
- Should `.raw()` method exist on all query builders?
    - I like the idea, but how?

---

## URL & Query Construction

### Q26: URL Construction Fragility
**What:** URLs are built by string concatenation or f-strings. No URL validation.

**Why it matters:** Easy to create malformed URLs. Potential for injection if user input is used.

**Affected code:**
- `bcb/currency.py` L23–27
- `bcb/sgs/__init__.py` L83–86
- `bcb/odata/framework.py` L510 (uses `quote()` for params, good)

**Questions:**
- Should we use `urllib.parse` utilities for URL construction?
    - Yes, we should.
- Should URLs be validated before making requests?
    - Yes, they should.
- Should user-provided filter values be escaped/validated?
    - Yes, they should.

---

### Q27: OData Filter Injection Vulnerability
**What:** `ODataPropertyFilter.statement()` builds filter strings. If a user constructs a filter with special characters, it could break the query.

**Why it matters:** While unlikely in practice (type checking), it's a potential security issue.

**Affected code:**
- `bcb/odata/framework.py` L171–181

**Questions:**
- Should filter values be escaped/quoted for OData syntax?
    - The values are OData standard.
- Should we use a library like `odata-query` for safer query building?
    - Yes, we should.
- Are there SQL/NoSQL-like injection attacks possible with OData filters?
    - No, there are not.

---

## Testing & Quality

### Q28: Flaky Tests
**What:** Some tests use `@mark.flaky` annotation for transient failures.

**Why it matters:** CI/CD reliability. Hard to know if a test failure is real or a fluke.

**Affected code:**
- Multiple files (see with `grep -r "@mark.flaky"`)

**Questions:**
- Which tests are flaky? Why?
    - yes, the BCB network is unstable.
- Should we improve network mocking in tests instead of allowing flakiness?
    - Yes, we should.
- What's the max retry count? Is that configurable?
    - No, it is not configurable, bu it could.
- Should flaky tests be separated into a different suite?
    - Yes, they should.

---

### Q29: Limited Negative Test Cases
**What:** Most tests check the happy path. Few test error conditions.

**Why it matters:** Errors might not be handled correctly in production.

**Affected code:**
- Tests generally lack "test_*_error", "test_*_invalid", etc.

**Questions:**
- Should we test each module's error handling more thoroughly?
    - Yes, we should.
- Should we test malformed input (bad dates, invalid symbols, etc.)?
    - Yes, we should.
- Should we test API failures (500s, timeouts, malformed responses)?
    - Yes, we should.

---

### Q30: Test Isolation & Fixture Reuse
**What:** `conftest.py` has many hardcoded mock data constants. Tests import and reuse them.

**Why it matters:** Changes to mock data can break many tests. Hard to test edge cases.

**Affected code:**
- `tests/conftest.py` L8–74

**Questions:**
- Should mock data be generated dynamically (e.g., factory functions)?
    - Yes, it should.
- Should we use `pytest` fixtures for each mock data type?
    - Yes, we should.
- Should we test with both minimal and large datasets?
    - Yes, it should.

---

## Performance & Scalability

### Q31: No Pagination Support
**What:** OData queries don't expose pagination controls clearly. Users might not know about `$top` and `$skip`.

**Why it matters:** Large result sets might be slow or fail. Users might not know how to fetch data in chunks.

**Affected code:**
- `bcb/odata/api.py` L120–166 (takes `limit` and `skip` but no clear pagination docs)

**Questions:**
- Should pagination be documented more prominently?
    - Yes, it should.
- Should there be a convenience method for iterating through pages?
    - Yes, it should.
- Should there be a warning if a query returns a very large result set?
    - Yes, there should.

---

### Q32: No Async Support
**What:** All I/O is synchronous. No async/await API.

**Why it matters:** For async applications or heavy batch processing, sync I/O can be a bottleneck.

**Affected code:**
- All HTTP calls throughout the codebase

**Questions:**
- Is async support needed or planned?
    - Yes, it is.
- Would `httpx` async API be used? Or a separate async module?
    - What is the best alternative? Pros and cons of each.
- Should we design the current API to be easily async-compatible?
    - Yes, we should.

---

### Q33: No Batch Request Support
**What:** Each request is independent. No bulk/batch endpoint for multiple queries.

**Why it matters:** Fetching multiple series one-by-one can be slow.

**Affected code:**
- `bcb/sgs/__init__.py` (makes N requests for N series)

**Questions:**
- Do BCB APIs support batch/bulk requests?
    No, they don´t.
- Could we optimize `sgs.get([code1, code2, ...])` to be faster?
    - Yes, we could.
- Should there be a batch context manager?
    - Yes, there should.

---

## Configuration & Customization

### Q34: Magic Strings & Constants
**What:** Hard-coded service URLs, column names, date formats, etc.

**Why it matters:** Changing format or API requires code changes. Not flexible for testing/mocking.

**Affected code:**
- `bcb/odata/api.py` L13 (OLINDA_BASE_URL)
- `bcb/sgs/__init__.py` L83 (hardcoded BCB URL)
- Many magic numbers and strings throughout

**Questions:**
- Should configuration be externalizable (env vars, config files)?
    - No, there should not.
- Should there be a config class or module?
    - No, there should not.
- Should timeout, retry count, etc. be configurable?
    - Yes, they should.

---

### Q35: No Logging
**What:** No `logging` module usage anywhere. Errors are silent or use `warnings`.

**Why it matters:** Hard to debug issues in production. No audit trail.

**Affected code:**
- Throughout (no logging imports)

**Questions:**
- Should we add structured logging?
    Yes, we should.
- Should HTTP requests/responses be logged (with PII scrubbing)?
    - I have never heard about that.
- Should there be debug-level logs for troubleshooting?
    - Yes, there should.

---

## API Design

### Q36: Endpoint Access Pattern
**What:** Users access endpoints via `api.get_endpoint("EntitySetName")`. Endpoint names are strings.

**Why it matters:** No IDE autocomplete. Easy to misspell endpoint names.

**Affected code:**
- `bcb/odata/api.py` L217–239

**Questions:**
- Could we expose endpoint names as constants or enums?
    - No, we could not, these endpoint names are dynamic.
- Could we generate a typed API with properties for each endpoint (like mypy plugin)?
    - No, we could not, these endpoint names are dynamic.
- Should there be a `.describe()` output that lists available endpoints?
    - Yes, maybe.

---

### Q37: Filter/OrderBy Chaining
**What:** Filters and order-by are passed to `.get()` as positional args. Chaining via `.query()` is less discoverable.

**Why it matters:** Not obvious that chaining is possible.

**Affected code:**
- `bcb/odata/api.py` L120–166 vs. L168–176

**Questions:**
- Should `.get()` and `.query()` be merged into a single fluent API?
    - No, they should not.
- Should `.get()` accept `filter=`, `orderby=`, etc. as keyword args?
    - Yes, it should.

---

## Documentation & Examples

### Q38: Missing Usage Examples
**What:** README and docstrings have few real-world examples.

**Why it matters:** Users unsure how to use the API.

**Affected code:**
- README.md has high-level examples but not detailed ones
- Docstrings lack "See Also" or example sections

**Questions:**
- Should there be an `examples/` directory with notebooks or scripts?
    - Yes, there should.
- Should docstrings include code examples?
    - Yes, they should.
- Should there be a FAQ for common use cases?
    - Yes, there should.

---

### Q39: Unclear Module Organization
**What:** Three main modules (sgs, currency, odata) but no overview of when to use each.

**Why it matters:** Users may use the wrong module for a task.

**Affected code:**
- Documentation doesn't clearly differentiate use cases

**Questions:**
- Should README have a decision tree (e.g., "use sgs for time series", "use currency for exchange rates")?
    - Yes, it should.
- Should there be a "which API to use" guide?
    - Yes, there should.

---

## Maintenance & Dependencies

### Q40: Dependency on BCB API Format Stability
**What:** Code assumes specific CSV/JSON formats from BCB APIs. Changes would require code updates.

**Why it matters:** If BCB changes format, the library breaks.

**Affected code:**
- Throughout (e.g., hardcoded column positions)

**Questions:**
- Should we have a schema version or format detection?
    - Yes, we should, but these formats difficultly change.
- Should there be deprecation warnings for old formats?
    - Yes, there should.
- Should we monitor BCB API for breaking changes?
    - Yes, we should.

---

### Q41: Build & Distribution
**What:** Using `uv` with hatchling. Good, but some concerns.

**Why it matters:** Users might have trouble installing with older tools.

**Affected code:**
- `pyproject.toml` L37–42

**Questions:**
- Should we support older Python versions (< 3.10)?
    - No, we should not.
- Are there known compatibility issues with pip/conda?
    - No, there are not.
- Should there be Windows/macOS-specific build requirements?
    - No, there should not.

---

## Security

### Q42: No Input Validation
**What:** User inputs (dates, symbols, codes) are not validated before use.

**Why it matters:** Garbage in, garbage out. Silent failures or confusing errors.

**Affected code:**
- Functions accept user inputs without validation

**Questions:**
- Should we validate date ranges (e.g., start <= end)?
    - No, we should not.
- Should we validate currency symbols against a whitelist?
    - No, we should not.
- Should we validate SGS codes (e.g., are they positive integers)?
    - Yes, positive integers is ok, but that's all, I don't have a previous list to validate them.

---

### Q43: No Rate Limiting / Quota Handling
**What:** No protection against hitting BCB API rate limits.

**Why it matters:** Users can accidentally hammer the API and get blocked.

**Affected code:**
- All HTTP request code

**Questions:**
- Should we implement client-side rate limiting?
    - No, we should not.
- Should we detect and handle 429 (Too Many Requests) responses?
    - Yes, if the server answers 429 we should inform the user.
- Should we warn users about API quotas?
    - No, we should not.

---

### Q44: Metadata URL Hardcoding
**What:** OData metadata URL is constructed from service URL with a hardcoded `$metadata` suffix.

**Why it matters:** If BCB changes this pattern, code breaks. Could be discovered dynamically.

**Affected code:**
- `bcb/odata/framework.py` L362

**Questions:**
- Could metadata URL be discovered from the service root response?
    No, OData is a standard.
- Should it be configurable?
    - No, we should not.

---

## Misc / Design Questions

### Q45: Date Class Utility
**What:** `bcb/utils.py` has a `Date` class that wraps Python `date` objects.

**Why it matters:** Another abstraction to learn. Why not use `datetime`/`date` directly?

**Affected code:**
- `bcb/utils.py` L18–58
- Throughout as `DateInput` type alias

**Questions:**
- Why was `Date` class created instead of using standard library `date`?
    - `Date` and `DateInput` allow the users to provide date in different formats.
- Does it add value over `datetime.date`?
    - Yes, it does add  flexbility to the user.
- Could we simplify by removing the class and using `date` directly?
    - No, we could not.

---

### Q46: Endpoint.describe() Output
**What:** `.describe()` method prints to stdout. No structured output.

**Why it matters:** Hard to parse programmatically. Can't redirect to file easily.

**Affected code:**
- `bcb/odata/framework.py` L75–82, L96–112
- `bcb/odata/framework.py` L515–542 (in ODataQuery)
- `bcb/odata/api.py` L195–215

**Questions:**
- Should `.describe()` return a dict/dataclass instead of printing?
    - No, it should not.
- Should there be a `.to_string()` method for formatting?
    - No, there should not.
- Should structured output be available in multiple formats (JSON, YAML, etc.)?
    - No, it should not.

---

### Q47: SGSCode Design
**What:** `SGSCode` wraps int/str codes. Supports named codes but design is a bit awkward.

**Why it matters:** API could be clearer.

**Affected code:**
- `bcb/sgs/__init__.py` L32–43

**Questions:**
- Should `SGSCode` be a dataclass?
    - Yes, it should.
- Should there be separate constructors for named vs. unnamed codes?
    - Yes, there should.
- Could `__repr__` be improved to clarify meaning?
    - Yes, it could.

---

### Q48: Overload Declarations Completeness
**What:** Many functions use `@overload` but not exhaustively for all parameter combinations.

**Why it matters:** Type checkers may not infer correct return types in all cases.

**Affected code:**
- `bcb/currency.py` L176–204
- `bcb/sgs/__init__.py` L105–137
- `bcb/odata/api.py` L53–62

**Questions:**
- Are all return type combinations covered?
    - Yes, they are.
- Should we test overload declarations with a type checker?
    - No, we should not.
- Are overloads necessary or could we simplify with Union types?
    - You tell me.

---

### Q49: Relative vs Absolute Imports
**What:** Most imports are relative (from `bcb.exceptions import`). Some mix relative and absolute.

**Why it matters:** Minor but affects readability and IDE support.

**Affected code:**
- Throughout, mostly consistent but worth reviewing

**Questions:**
- Should we standardize on absolute imports across the codebase?
    - Yes, we should.
- Should we use `from __future__ import annotations` for forward references?
    - Yes, we should.

---

### Q50: Future-Proofing
**What:** Code is fairly rigid. Changes to BCB APIs would require refactoring.

**Why it matters:** Library may need rapid updates for API changes.

**Affected code:**
- Architecture throughout

**Questions:**
- Should we design for easier versioning of API schemas?
    - Yes, we should.
- Should there be a plugin/provider system for different API versions?
    - No, there should not.
- Should we version APIs (e.g., `sgs_v1`, `sgs_v2`)?
    - Yes, we should.

---

## Summary

This document captures **50 questions/concerns** organized into **10 categories**:
1. HTTP Client & Connection Management (4 questions)
2. Caching & State Management (4 questions)
3. Error Handling & Exceptions (5 questions)
4. Data Parsing & Validation (4 questions)
5. Type Safety & Annotations (3 questions)
6. Code Quality & Documentation (3 questions)
7. Architecture & API Consistency (3 questions)
8. URL & Query Construction (2 questions)
9. Testing & Quality (3 questions)
10. Performance & Scalability (3 questions)
11. Configuration & Customization (2 questions)
12. API Design (2 questions)
13. Documentation & Examples (2 questions)
14. Maintenance & Dependencies (2 questions)
15. Security (3 questions)
16. Misc / Design Questions (6 questions)

**Next Steps:** Please review and answer these questions in this document. Your answers will inform the implementation plan for improvements.
