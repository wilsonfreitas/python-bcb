# Plan: Add `output="text"` to All BCB Modules

## Context

The package's primary purpose is fetching BCB API data into pandas DataFrames. Users building SOR/SOT/SPEC data pipelines need to persist raw downloaded data before transformation — it's bad practice to serialize a DataFrame back to text (lossy, format-dependent). Each BCB module already holds the raw text internally but doesn't expose it. This plan adds `output="text"` to all public `get()` / `collect()` functions so pipelines can save the exact bytes returned by BCB before any pandas processing.

---

## Scope

All three modules: **OData**, **SGS**, **Currency**

---

## Interface

Add `output: str = "dataframe"` parameter to:
- `EndpointQuery.collect(output=...)` → `"dataframe"` returns `pd.DataFrame`, `"text"` returns `str`
- `Endpoint.get(*args, output=..., **kwargs)` → same
- `sgs.get(codes, ..., output=...)` → `"dataframe"` unchanged, `"text"` returns `str` (single code) or `dict[int, str]` (multiple codes, keyed by code value)
- `currency.get(symbols, ..., output=...)` → `"dataframe"` unchanged, `"text"` returns `str` (single symbol) or `dict[str, str]` (multiple symbols, keyed by ISO symbol)

Use `@overload` + `Literal["text", "dataframe"]` for mypy --strict compliance on each function.

---

## What "text" contains per module

| Module | Raw text format | Source |
|--------|----------------|--------|
| OData  | OData JSON response: `{"@odata.context": "...", "value": [...]}` | `ODataQuery.text()` (already exists in `framework.py:505`) |
| SGS    | BCB SGS JSON array: `[{"data": "01/01/2024", "valor": "100.5"}, ...]` | `sgs.get_json()` (already exists in `sgs/__init__.py:160`) |
| Currency | BCB PTAX semicolon-delimited CSV | `res.text` inside `_get_symbol()` |

---

## File Changes

### 1. `bcb/odata/api.py`

**`EndpointQuery.collect()`** — add `output` param:
```python
def collect(self, output: str = "dataframe") -> Union[pd.DataFrame, str]:
    if output == "text":
        return self.text()  # inherited from ODataQuery in framework.py:505
    # ... existing DataFrame logic unchanged
```

**`Endpoint.get()`** — intercept `output` kwarg before it reaches `_query.parameters()`:
```python
output_format = "dataframe"
for k, val in kwargs.items():
    if k == "limit": ...
    elif k == "output":
        output_format = val
    else:
        _query.parameters(**{k: val})
...
data = _query.collect(output=output_format)
```

Add `@overload` stubs and update return type to `Union[pd.DataFrame, str]`.

### 2. `bcb/sgs/__init__.py`

**`sgs.get()`** — add `output` param with early-return branch:
```python
def get(codes, start, end, last, multi, freq, output="dataframe"):
    if output == "text":
        results = {c.value: get_json(c.value, start, end, last) for c in _codes(codes)}
        # single code → str, multiple codes → dict[int, str]
        values = list(results.values())
        return values[0] if len(values) == 1 else results
    # ... existing DataFrame logic unchanged
```

Add `@overload` stubs:
- `output: Literal["dataframe"]` → `Union[pd.DataFrame, List[pd.DataFrame]]`
- `output: Literal["text"]` → `Union[str, dict[int, str]]`

### 3. `bcb/currency.py`

**New helper `_fetch_symbol_response()`**: extracts shared HTTP logic from `_get_symbol()` to avoid duplication.

```python
def _fetch_symbol_response(symbol, start_date, end_date) -> Optional[httpx.Response]:
    try:
        cid = _get_currency_id(symbol)
    except CurrencyNotFoundError:
        return None
    res = httpx.get(_currency_url(cid, start_date, end_date), follow_redirects=True)
    if res.headers["Content-Type"].startswith("text/html"):
        # existing HTML error warn logic (moved from _get_symbol)
        return None
    return res

def _get_symbol(symbol, start_date, end_date) -> Optional[pd.DataFrame]:
    res = _fetch_symbol_response(symbol, start_date, end_date)
    if res is None:
        return None
    # ... existing CSV parse logic (unchanged)

def _get_symbol_text(symbol, start_date, end_date) -> Optional[str]:
    res = _fetch_symbol_response(symbol, start_date, end_date)
    return res.text if res is not None else None
```

**`currency.get()`** — add `output` param:
```python
if output == "text":
    results = {s: _get_symbol_text(s, start, end) for s in symbols}
    results = {k: v for k, v in results.items() if v is not None}
    if not results:
        raise CurrencyNotFoundError(...)
    return results[symbols[0]] if len(symbols) == 1 else results
```

Add `@overload` stubs:
- `output: Literal["dataframe"]` → `pd.DataFrame`
- `output: Literal["text"]` → `Union[str, dict[str, str]]`

---

## Tests

Add to existing test files (using mocked HTTP via `pytest-httpx`):

- **`tests/test_odata.py`**: `EndpointQuery.collect(output="text")` returns str; `Endpoint.get(output="text")` returns str.
- **`tests/test_sgs.py`**: `sgs.get(1, ..., output="text")` returns `str`; `sgs.get([1, 2], ..., output="text")` returns `dict[int, str]`.
- **`tests/test_currency.py`**: `currency.get("USD", ..., output="text")` returns `str`; `currency.get(["USD", "EUR"], ..., output="text")` returns `dict[str, str]`.

---

## Verification

```bash
# Unit tests (mocked)
poetry run pytest -m "not integration" tests/test_odata.py tests/test_sgs.py tests/test_currency.py

# Type check
poetry run mypy bcb/

# Quick smoke test (live)
poetry run python -c "
from bcb import sgs
text = sgs.get(1, last=3, output='text')
print(type(text), text[:80])
"
```
