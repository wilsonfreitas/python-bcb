# Phase 2: Exception Hierarchy & Error Handling — Detailed Review

## Objetivo
Implementar fail-fast em todo o codebase, tornando `BCBAPIError.status_code` obrigatório, adicionando exceções especializadas para HTTP status codes, e removendo padrões de retorno `None` + `warnings.warn()`.

---

## 1️⃣ Mudanças em `bcb/exceptions.py`

### Estrutura atual:
```python
class BCBError(Exception):
    """Base exception for all python-bcb errors."""

class BCBAPIError(BCBError):
    """HTTP or API-level error from BCB."""
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code

class CurrencyNotFoundError(BCBError):
    """Raised when a requested currency symbol is not found."""

class SGSError(BCBError):
    """Raised for SGS-specific API errors."""

class ODataError(BCBError):
    """Raised for OData query/metadata errors."""
```

### Mudanças necessárias:

#### A) Tornar `status_code` obrigatório em `BCBAPIError`
```python
class BCBAPIError(BCBError):
    """HTTP or API-level error from BCB."""

    def __init__(self, message: str, status_code: int):  # ← Required, not Optional
        super().__init__(message)
        self.status_code = status_code
```

#### B) Adicionar exceções especializadas para HTTP status codes
```python
class BCBAPINotFoundError(BCBAPIError):
    """Raised when API returns 404 Not Found."""
    pass

class BCBRateLimitError(BCBAPIError):
    """Raised when API returns 429 Too Many Requests."""
    pass

class BCBAPIServerError(BCBAPIError):
    """Raised when API returns 5xx Server Error."""
    pass
```

---

## 2️⃣ Mudanças em `bcb/currency.py`

### Problema 1: `warnings.warn()` em L183

**Localização:** `_fetch_symbol_response()` (L165-185)

**Código atual:**
```python
def _fetch_symbol_response(
    symbol: str, start_date: DateInput, end_date: DateInput
) -> Optional["httpx.Response"]:
    try:
        cid = _get_currency_id(symbol)
    except CurrencyNotFoundError:
        return None
    url = _currency_url(cid, start_date, end_date)
    res = _CLIENT.get(url)
    if res.headers["Content-Type"].startswith("text/html"):
        # BCB returned HTML error page (e.g., no data for date range)
        doc = html.parse(BytesIO(res.content)).getroot()
        xpath = "//div[@class='msgErro']"
        elm = doc.xpath(xpath)[0]
        x = elm.text
        x = re.sub(r"^\W+", "", x)
        x = re.sub(r"\W+$", "", x)
        msg = f"BCB API returned error: {x} - {symbol}"
        warnings.warn(msg)      # ← Problem: Silent warning, caller might miss
        return None             # ← Returns None instead of raising
    return res
```

**Mudança:**
- Remover `warnings.warn()` (L183)
- Remover `return None` (L184)
- Levantar `BCBAPIError` em vez:

```python
def _fetch_symbol_response(
    symbol: str, start_date: DateInput, end_date: DateInput
) -> "httpx.Response":  # ← No longer Optional
    try:
        cid = _get_currency_id(symbol)
    except CurrencyNotFoundError:
        raise  # ← Propagate immediately (fail-fast)
    url = _currency_url(cid, start_date, end_date)
    res = _CLIENT.get(url)
    if res.headers["Content-Type"].startswith("text/html"):
        # BCB returned HTML error page
        doc = html.parse(BytesIO(res.content)).getroot()
        xpath = "//div[@class='msgErro']"
        elm = doc.xpath(xpath)[0]
        x = elm.text
        x = re.sub(r"^\W+", "", x)
        x = re.sub(r"\W+$", "", x)
        msg = f"BCB API returned error: {x} - {symbol}"
        raise BCBAPIError(msg, status_code=400)  # ← Raise instead of warn
    return res
```

### Problema 2: Função retorna `None` para "não encontrado"

**Localização:** `_get_symbol()` (L188-193)

**Código atual:**
```python
def _get_symbol(
    symbol: str, start_date: DateInput, end_date: DateInput
) -> Optional[pd.DataFrame]:
    res = _fetch_symbol_response(symbol, start_date, end_date)
    if res is None:
        return None  # ← Silently skips symbol
    # ... rest of parsing
```

**Mudança:**
Depois que `_fetch_symbol_response` levantar exceções, não há mais `None`:

```python
def _get_symbol(
    symbol: str, start_date: DateInput, end_date: DateInput
) -> pd.DataFrame:  # ← No longer Optional
    res = _fetch_symbol_response(symbol, start_date, end_date)
    # res is guaranteed to be a Response (or exception raised)
    # ... rest of parsing
```

### Problema 3: `get()` silenciosamente descarta símbolos inválidos

**Localização:** `get()` (linha ~235-280)

**Código atual:**
```python
def get(
    symbols: Union[str, List[str]],
    start: DateInput,
    end: DateInput,
    side: str = "ask",
    groupby: str = "symbol",
    output: str = "dataframe",
) -> Union[pd.DataFrame, str, Dict[str, str]]:
    # ... code ...
    for symbol in symbols:
        df = _get_symbol(symbol, start_date, end_date)
        if df is None:
            continue  # ← Silently skip invalid symbol
        # ... accumulate results
    if not results:
        raise CurrencyNotFoundError(...)  # ← Only raise if ALL failed
```

**Problema:** `get(["USD", "BOGUS"])` silenciosamente descarta `BOGUS` sem aviso.

**Mudança:** Depois que `_get_symbol` levantar exceções, `BOGUS` vai levantar imediatamente:

```python
def get(
    symbols: Union[str, List[str]],
    start: DateInput,
    end: DateInput,
    side: str = "ask",
    groupby: str = "symbol",
    output: str = "dataframe",
) -> Union[pd.DataFrame, str, Dict[str, str]]:
    # ... code ...
    for symbol in symbols:
        df = _get_symbol(symbol, start_date, end_date)  # ← Raises on error
        # ... accumulate results
    # results will always be populated or exception raised
```

### Tipo de retorno não-Optional

Remover `Optional` de:
- L168: `_fetch_symbol_response()` → `"httpx.Response"` (não `Optional["httpx.Response"]`)
- L190: `_get_symbol()` → `pd.DataFrame` (não `Optional[pd.DataFrame]`)
- L213: `_get_symbol_text()` → `str` (não `Optional[str]`)

---

## 3️⃣ Mudanças em `bcb/sgs/__init__.py`

### Problema: Bare `except Exception` em L253

**Localização:** `get_json()` (L250-254)

**Código atual:**
```python
if res.status_code != 200:
    try:
        res_json = json.loads(res.text)
    except Exception:  # ← TOO BROAD
        res_json = {}
    if "error" in res_json:
        raise SGSError(...)
    elif "erro" in res_json:
        raise SGSError(...)
    raise SGSError(...)
```

**Problema:** `except Exception` pega tudo, incluindo `AttributeError`, `TypeError`, etc.

**Mudança:**
```python
if res.status_code != 200:
    try:
        res_json = json.loads(res.text)
    except json.JSONDecodeError:  # ← Specific exception
        res_json = {}
    if "error" in res_json:
        raise SGSError(...)
    elif "erro" in res_json:
        raise SGSError(...)
    raise SGSError(...)
```

### Adicionar detecção de 429 em `get_json()`

```python
if res.status_code == 429:
    raise BCBRateLimitError(
        "BCB API rate limit exceeded. Please try again later.",
        status_code=429
    )
if res.status_code != 200:
    # ... existing error handling
```

---

## 4️⃣ Mudanças em `bcb/currency.py` — Detecção de 429

**Localização:** `_currency_id_list()` (L49-64)

**Código atual:**
```python
def _currency_id_list() -> pd.DataFrame:
    # ...
    res = _CLIENT.get(url1)
    if res.status_code != 200:
        msg = f"BCB API Request error, status code = {res.status_code}"
        raise BCBAPIError(msg, res.status_code)
```

**Mudança:** Adicionar detecção de 429:

```python
def _currency_id_list() -> pd.DataFrame:
    # ...
    res = _CLIENT.get(url1)
    if res.status_code == 429:
        raise BCBRateLimitError(
            "BCB API rate limit exceeded",
            status_code=429
        )
    if res.status_code != 200:
        msg = f"BCB API Request error, status code = {res.status_code}"
        raise BCBAPIError(msg, res.status_code)
```

Também em `_fetch_symbol_response()` (após chamada a `_CLIENT.get(url)`).

---

## 5️⃣ Import necessário

Adicionar a `bcb/currency.py`:

```python
from bcb.exceptions import (
    BCBAPIError,
    BCBRateLimitError,
    CurrencyNotFoundError,
)
```

---

## 📋 Checklist Phase 2

**Arquivo: `bcb/exceptions.py`**
- [ ] Tornar `BCBAPIError.status_code` obrigatório (remove `Optional`)
- [ ] Adicionar `BCBAPINotFoundError(BCBAPIError)` (para 404)
- [ ] Adicionar `BCBRateLimitError(BCBAPIError)` (para 429)
- [ ] Adicionar `BCBAPIServerError(BCBAPIError)` (para 5xx) — optional

**Arquivo: `bcb/currency.py`**
- [ ] Remover `warnings.warn()` em `_fetch_symbol_response()`
- [ ] Mudar `_fetch_symbol_response()` para levantar em vez de retornar `None`
- [ ] Mudar tipo de retorno para `"httpx.Response"` (não `Optional`)
- [ ] Adicionar detecção de 429 em `_currency_id_list()`
- [ ] Adicionar detecção de 429 em `_fetch_symbol_response()`
- [ ] Remover `Optional` de `_get_symbol()` e `_get_symbol_text()`
- [ ] Remover `import warnings` (não mais usado)
- [ ] Atualizar imports de exceções

**Arquivo: `bcb/sgs/__init__.py`**
- [ ] Mudar `except Exception` → `except json.JSONDecodeError` (L253)
- [ ] Adicionar detecção de 429 em `get_json()`

**Testes:**
- [ ] Rodar `uv run pytest -m "not integration"` — alguns testes vão falhar por mudança de API
- [ ] Verificar `uv run mypy bcb/` — 0 errors
- [ ] Verificar `uv run ruff check bcb/` — all checks passed
- [ ] Verificar `uv run ruff format --check bcb/` — properly formatted

---

## 🔄 Impacto nos testes

Esses testes vão **FALHAR** após Phase 2 (porque a API mudou):
- `test_get_symbol_unknown_currency_returns_none` — agora levanta exceção
- `test_currency_get_unknown_symbol_raises` — nome enganoso, na verdade espera None
- Qualquer teste que chama `get(["BOGUS"])` sem expect exceção

Isso é **ESPERADO** — Phase 7 vai consertar os testes.

---

## ⚠️ Pontos de atenção

1. **Breaking change:** Funções que retornavam `None` agora levantam exceções
2. **Testes vão falhar:** Phase 7 vai atualizar os testes
3. **Retry automático:** O cliente HTTP vai automaticamente retry em 5xx (via tenacity)
4. **429 não tem retry:** Levantará `BCBRateLimitError` imediatamente (correto — não retry em rate limit)

---

## Decisões para você revisar:

1. **BCBAPIServerError para 5xx?** Adicionar ou manter genérico?
   - Opção A: Adicionar (mais específico)
   - Opção B: Manter genérico com `BCBAPIError(msg, status_code=500)`

2. **Tipo de retorno para `_fetch_symbol_response()`:**
   - Opção A: `"httpx.Response"` (nunca retorna None)
   - Opção B: Manter como está (mais compatível com testes antigos)

Recomendo Opção A em ambos.
