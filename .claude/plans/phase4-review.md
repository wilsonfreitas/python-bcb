# Phase 4: Data Validation & Types — Detailed Review

## Objetivo
Implementar validação robusta de dados (CSV, datas, tipos), converter SGSCode para dataclass com construtores separados, adicionar TypedDict para dict returns, e padronizar imports (absolutos + `from __future__ import annotations`).

---

## 1️⃣ CSV Validation em `bcb/currency.py`

### Problema atual:
```python
# L194-196
columns = ["Date", "aa", "bb", "cc", "bid", "ask", "dd", "ee"]
df = pd.read_csv(
    StringIO(res.text), delimiter=";", header=None, names=columns, dtype=str
)
```

**Problemas:**
- Sem validação do número de colunas
- Se BCB mudar para 9+ colunas, falha silenciosa
- Nomes de coluna "aa", "bb" são misteriosos

### Mudanças necessárias:

#### A) Validar número de colunas
```python
def _validate_currency_csv(csv_text: str) -> pd.DataFrame:
    """Parse and validate currency CSV format.

    Parameters
    ----------
    csv_text : str
        CSV content from BCB API

    Returns
    -------
    pd.DataFrame
        Parsed DataFrame with bid/ask columns

    Raises
    ------
    BCBAPIError
        If CSV format is invalid (wrong column count)
    """
    df = pd.read_csv(
        StringIO(csv_text),
        delimiter=";",
        header=None,
        dtype=str
    )

    # Validate column count
    if len(df.columns) != 8:
        raise BCBAPIError(
            f"Invalid CSV format: expected 8 columns, got {len(df.columns)}",
            status_code=400
        )

    # Assign meaningful names
    df.columns = ["Date", "_col1", "_col2", "_col3", "bid", "ask", "_col6", "_col7"]
    return df[["Date", "bid", "ask"]]
```

#### B) Remover `Optional` de _get_symbol return type (já feito em Phase 2)
- Já feito! ✓

---

## 2️⃣ Date Validation em `bcb/currency.py`

### Problema atual:
```python
# L197
df["Date"] = pd.to_datetime(df["Date"], format="%d%m%Y")
```

**Problemas:**
- Sem tratamento de erro se formato for inválido
- Silent failure se BCB mudar formato

### Mudanças necessárias:

```python
def _parse_currency_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Parse and validate date column in currency CSV.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with Date column as strings

    Returns
    -------
    pd.DataFrame
        DataFrame with parsed DatetimeIndex

    Raises
    ------
    BCBAPIError
        If date parsing fails
    """
    try:
        df["Date"] = pd.to_datetime(df["Date"], format="%d%m%Y")
    except ValueError as e:
        raise BCBAPIError(
            f"Failed to parse currency date column: {str(e)}",
            status_code=400
        )
    return df
```

---

## 3️⃣ Type Conversion Validation em `bcb/currency.py`

### Problema atual:
```python
# L190-191
df["code"] = df["code"].astype("int32")
df["symbol"] = df["symbol"].str.strip()
```

**Problemas:**
- `.astype("int32")` pode falhar silenciosamente
- Sem tratamento se dados tiverem valores não-numéricos

### Mudanças necessárias:

```python
def _parse_currency_types(df: pd.DataFrame) -> pd.DataFrame:
    """Parse and validate data types in currency DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with mixed types

    Returns
    -------
    pd.DataFrame
        DataFrame with validated types

    Raises
    ------
    BCBAPIError
        If type conversion fails
    """
    try:
        df["code"] = df["code"].astype("int32")
        df["country_code"] = df["country_code"].astype("int32")
    except (ValueError, TypeError) as e:
        raise BCBAPIError(
            f"Failed to parse currency numeric columns: {str(e)}",
            status_code=400
        )

    df["symbol"] = df["symbol"].str.strip()
    return df
```

---

## 4️⃣ SGSCode → Dataclass em `bcb/sgs/__init__.py`

### Problema atual:
```python
# L32-43
class SGSCode:
    def __init__(self, code: Union[str, int], name: Optional[str] = None) -> None:
        if name is None:
            if isinstance(code, int) or isinstance(code, str):  # ← Always true!
                self.name = str(code)
                self.value = int(code)
        else:
            self.name = str(name)
            self.value = int(code)

    def __repr__(self) -> str:
        return f"{self.value} - {self.name}" if self.name else f"{self.value}"
```

**Problemas:**
- Tipo annotation diz que `name` é `Optional[str]`, mas lógica é confusa
- Nested `if isinstance()` é sempre verdadeira (redundante)
- `__repr__` trata `self.name` como boolean (pode ser string vazia)

### Mudança necessária:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class SGSCode:
    """SGS time series code with optional human-readable name.

    Attributes
    ----------
    value : int
        Numeric SGS code
    name : str
        Human-readable name or string representation of code
    """

    value: int
    name: str

    @classmethod
    def from_code(cls, code: int | str) -> "SGSCode":
        """Create SGSCode from numeric or string code.

        Parameters
        ----------
        code : int | str
            SGS code

        Returns
        -------
        SGSCode
            New instance with name = str(code)
        """
        code_int = int(code)
        return cls(value=code_int, name=str(code_int))

    @classmethod
    def from_named(cls, code: int | str, name: str) -> "SGSCode":
        """Create SGSCode with explicit name.

        Parameters
        ----------
        code : int | str
            SGS code
        name : str
            Human-readable name

        Returns
        -------
        SGSCode
            New instance with value and name
        """
        return cls(value=int(code), name=name)

    def __repr__(self) -> str:
        return f"{self.value} - {self.name}"
```

### Impacto em `_codes()` generator (L55-68):

Atual:
```python
def _codes(codes: SGSCodeInput) -> Generator[SGSCode, None, None]:
    if isinstance(codes, (int, str)):
        yield SGSCode(codes)
    elif isinstance(codes, tuple):
        yield SGSCode(codes[0], codes[1])
    elif isinstance(codes, (list, tuple)):
        for code in codes:
            if isinstance(code, (int, str)):
                yield SGSCode(code)
            elif isinstance(code, tuple):
                yield SGSCode(code[0], code[1])
    elif isinstance(codes, Mapping):
        for name, code in codes.items():
            yield SGSCode(code, name)
```

Novo:
```python
def _codes(codes: SGSCodeInput) -> Generator[SGSCode, None, None]:
    """Normalize various SGSCodeInput formats to SGSCode instances."""
    if isinstance(codes, (int, str)):
        yield SGSCode.from_code(codes)
    elif isinstance(codes, tuple):
        yield SGSCode.from_named(codes[0], codes[1])
    elif isinstance(codes, (list, tuple)):
        for code in codes:
            if isinstance(code, (int, str)):
                yield SGSCode.from_code(code)
            elif isinstance(code, tuple):
                yield SGSCode.from_named(code[0], code[1])
    elif isinstance(codes, Mapping):
        for name, code in codes.items():
            yield SGSCode.from_named(code, name)
```

---

## 5️⃣ TypedDict para Dict Returns em `bcb/currency.py`

### Problema atual:
```python
# L446-453
@overload
def get(..., output: Literal["text"] = ...) -> Union[str, Dict[str, str]]: ...

def get(..., output: str = "dataframe") -> Union[pd.DataFrame, str, Dict[str, str]]:
    # Returns Dict[str, str] where keys=symbols, values=CSV text
```

**Problema:** Caller não sabe que dict keys são symbols e values são CSV text.

### Mudança necessária:

```python
from typing import TypedDict

class CurrencyTextResult(TypedDict):
    """Result from get() with output='text' and multiple symbols."""
    pass  # Really just Dict[str, str], but let's be explicit

# Better:
CurrencyTextResult = Dict[str, str]  # Maps symbol → CSV text

@overload
def get(
    symbols: str,  # Single symbol
    start: DateInput,
    end: DateInput,
    side: str = ...,
    groupby: str = ...,
    output: Literal["text"] = ...,
) -> str: ...  # Single symbol → string

@overload
def get(
    symbols: List[str],  # Multiple symbols
    start: DateInput,
    end: DateInput,
    side: str = ...,
    groupby: str = ...,
    output: Literal["text"] = ...,
) -> Dict[str, str]: ...  # Multiple symbols → dict
```

---

## 6️⃣ Absolute Imports + `from __future__ import annotations`

### Atual (mixed):
```python
# bcb/currency.py
from .exceptions import BCBAPIError          # ← Relative
from bcb.utils import Date, DateInput         # ← Absolute

# bcb/sgs/__init__.py
from bcb.exceptions import SGSError          # ← Absolute
from bcb.utils import Date, DateInput         # ← Absolute

# bcb/odata/framework.py
from bcb.exceptions import ODataError        # ← Absolute
```

### Mudança necessária:

**Adicionar em TODAS as files de bcb/**:
```python
from __future__ import annotations

# Then use absolute imports everywhere:
from bcb.exceptions import ...
from bcb.utils import ...
from bcb.http import ...
```

**Benefit:**
- Type hints podem referenciar tipos definidos depois (forward references)
- Evita circular imports com strings
- Padrão do PEP 563

---

## 7️⃣ SGS Input Validation em `bcb/sgs/__init__.py`

### Problema atual:
```python
# L55-68 (after our SGSCode refactor)
def _codes(codes: SGSCodeInput) -> Generator[SGSCode, None, None]:
    # ... generator ...
    # No validation that int codes are positive
```

### Mudança necessária:

```python
def _codes(codes: SGSCodeInput) -> Generator[SGSCode, None, None]:
    """Normalize SGSCodeInput to SGSCode instances.

    Raises
    ------
    ValueError
        If any code is a non-positive integer
    """
    if isinstance(codes, (int, str)):
        code_obj = SGSCode.from_code(codes)
        _validate_sgs_code(code_obj)
        yield code_obj
    # ... rest similar but with validation ...

def _validate_sgs_code(code: SGSCode) -> None:
    """Validate SGSCode value.

    Parameters
    ----------
    code : SGSCode
        Code to validate

    Raises
    ------
    ValueError
        If code value is not positive integer
    """
    if code.value <= 0:
        raise ValueError(
            f"SGS code must be positive integer, got {code.value}"
        )
```

---

## 📋 Checklist Phase 4

**CSV Validation (`bcb/currency.py`)**
- [ ] Create `_validate_currency_csv()` function
- [ ] Create `_parse_currency_dates()` function
- [ ] Create `_parse_currency_types()` function
- [ ] Update `_get_symbol()` to use validation functions
- [ ] Add try/except with BCBAPIError raises

**Type Annotations (`bcb/currency.py`, `bcb/sgs/__init__.py`)**
- [ ] Add `from __future__ import annotations` to all bcb/ files
- [ ] Convert all imports to absolute (from bcb.xxx import)
- [ ] Add `CurrencyTextResult` TypedDict (or just use Dict[str, str] with better docs)
- [ ] Add/update overloads for single vs multiple symbol returns

**SGSCode Refactor (`bcb/sgs/__init__.py`)**
- [ ] Convert SGSCode to @dataclass(frozen=True)
- [ ] Add `from_code()` classmethod
- [ ] Add `from_named()` classmethod
- [ ] Update `__repr__()` to be simpler
- [ ] Add `_validate_sgs_code()` function
- [ ] Update `_codes()` generator to use classmethods + validation
- [ ] Remove nested `if isinstance()` check

**Global Changes (all bcb/ modules)**
- [ ] Add `from __future__ import annotations` at top of each file
- [ ] Convert all relative imports to absolute imports
- [ ] Verify mypy still passes
- [ ] Verify ruff check passes
- [ ] Verify ruff format passes

**Tests**
- [ ] Run pytest: expect same 24 passed
- [ ] No new failures expected (only improvements to error handling)

---

## ⚠️ Pontos de atenção

1. **SGSCode breaking change**: Refactoring para dataclass muda construtor
   - Antigo: `SGSCode(123)` ou `SGSCode(123, "name")`
   - Novo: `SGSCode.from_code(123)` ou `SGSCode.from_named(123, "name")`
   - Mas `SGSCode(value=123, name="123")` também funciona (dataclass)

2. **Date parsing errors**: Mudança de silent failure → exception
   - Se BCB mudar formato de data, agora vai levantar `BCBAPIError` com mensagem clara

3. **TypedDict não é necessário**: Se Dict[str, str] é claro o suficiente
   - Mais útil seria adicionar docstring clara ao `get()` explicando keys/values

4. **Imports change is global**: Vai afetar todos os 10 arquivos do bcb/
   - Mas é mudança mecânica, sem risco

---

## Decisões para você revisar:

1. **Manter SGSCode como dataclass ou voltar para classe simples?**
   - Recomendo: **Dataclass** (mais limpo, imutável com frozen=True)

2. **TypedDict para CurrencyTextResult ou deixar como Dict[str, str]?**
   - Recomendo: **TypedDict** (mais documentação + type hints)

3. **Validar todas as conversões de tipo ou apenas as críticas?**
   - Recomendo: **Todas** (robustez)

4. **Qual should be the minimum positive integer para SGS codes?**
   - Recomendo: **> 0** (apenas positivos, nada de 0 ou negativos)
