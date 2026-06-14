from __future__ import annotations

import asyncio
import logging
import re
import threading
from datetime import date, timedelta
from io import BytesIO, StringIO
from typing import Dict, List, Literal, NamedTuple, NoReturn, Union, overload
from urllib.parse import urlencode

import httpx
import numpy as np
import pandas as pd
from lxml import etree, html

from bcb.http import (
    get_async_client,
    get_client,
    raise_for_request_error,
    raise_for_status,
)
from bcb.exceptions import BCBAPIError, CurrencyNotFoundError
from bcb.utils import Date, DateInput

logger = logging.getLogger(__name__)

"""
O módulo :py:mod:`bcb.currency` tem como objetivo fazer consultas no site do conversor de moedas do BCB.
"""


def _currency_url(currency_id: int, start_date: DateInput, end_date: DateInput) -> str:
    start_date = Date(start_date)
    end_date = Date(end_date)
    params = urlencode(
        {
            "method": "gerarCSVFechamentoMoedaNoPeriodo",
            "ChkMoeda": currency_id,
            "DATAINI": start_date.date.strftime("%d/%m/%Y"),
            "DATAFIM": end_date.date.strftime("%d/%m/%Y"),
        }
    )
    return f"https://ptax.bcb.gov.br/ptax_internet/consultaBoletim.do?{params}"


class _CacheKey(NamedTuple):
    """Structured cache key for currency module.

    Attributes
    ----------
    type : str
        Cache type: "currency_id_list" or "currency_list"
    """

    type: str

    def __repr__(self) -> str:
        return f"CacheKey(type={self.type!r})"


class _ThreadSafeCache:
    """Thread-safe cache wrapper for currency data.

    Parameters
    ----------
    initial_data : dict, optional
        Initial cache data (default: empty)
    """

    def __init__(self, initial_data: dict[_CacheKey, pd.DataFrame] | None = None):
        self._lock = threading.RLock()
        self._data: dict[_CacheKey, pd.DataFrame] = initial_data or {}

    def get(self, key: _CacheKey) -> pd.DataFrame | None:
        """Get value from cache.

        Parameters
        ----------
        key : _CacheKey
            Cache key

        Returns
        -------
        pd.DataFrame | None
            Cached DataFrame or None if not found
        """
        with self._lock:
            return self._data.get(key)

    def set(self, key: _CacheKey, value: pd.DataFrame) -> None:
        """Set value in cache.

        Parameters
        ----------
        key : _CacheKey
            Cache key
        value : pd.DataFrame
            DataFrame to cache
        """
        with self._lock:
            self._data[key] = value

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._data.clear()


# Default module-level cache instance
_DEFAULT_CACHE = _ThreadSafeCache()


def clear_cache(cache: _ThreadSafeCache | None = None) -> None:
    """Clear the module-level session cache.

    :func:`get` and :func:`get_currency_list` cache the currency ID list and
    the full currency master table for the duration of the Python session so
    that repeated calls do not make redundant HTTP requests.  Call this
    function to force a fresh fetch on the next request (useful in tests or
    long-running scripts where the master data may have changed).

    Parameters
    ----------
    cache : _ThreadSafeCache, optional
        Cache instance to clear. If None, uses module-level default.
    """
    (cache or _DEFAULT_CACHE).clear()


def _currency_id_list(
    cache: _ThreadSafeCache | None = None,
) -> pd.DataFrame:
    """Fetch list of available currency IDs and names.

    Parameters
    ----------
    cache : _ThreadSafeCache, optional
        Cache instance to use. If None, uses module-level default.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns: name, id

    Raises
    ------
    BCBRateLimitError
        If API rate limit is exceeded (429)
    BCBAPINotFoundError
        If API endpoint not found (404)
    BCBAPIError
        If API returns error response
    """
    cache = cache or _DEFAULT_CACHE
    cache_key = _CacheKey(type="currency_id_list")
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    url1 = (
        "https://ptax.bcb.gov.br/ptax_internet/consultaBoletim.do?"
        "method=exibeFormularioConsultaBoletim"
    )
    logger.debug(f"Fetching currency ID list from {url1}")
    try:
        res = get_client().get(url1)
    except httpx.HTTPError as ex:
        raise_for_request_error(ex, context="Currency ID list")
    logger.debug(
        f"Currency ID list response: status={res.status_code}, length={len(res.content)}"
    )
    raise_for_status(
        res,
        context="Currency ID list",
        not_found_message="BCB API endpoint not found (404)",
    )

    doc = html.parse(BytesIO(res.content)).getroot()
    xpath = "//select[@name='ChkMoeda']/option"
    x = [(elm.text, elm.get("value")) for elm in doc.xpath(xpath)]
    df = pd.DataFrame(x, columns=["name", "id"])
    df["id"] = df["id"].astype("int32")
    cache.set(cache_key, df)
    return df


def _get_valid_currency_list(
    _date: date, n: int = 0, max_rollback: int = 30
) -> "httpx.Response":
    """Fetch currency list CSV, rolling back dates if necessary.

    Attempts to fetch the currency master file for the given date.
    If the file doesn't exist (common for weekends/holidays), rolls back
    to the previous day and retries. Connection errors trigger retries
    on the same date.

    Parameters
    ----------
    _date : date
        Target date to fetch
    n : int
        Current connection retry attempt (internal use)
    max_rollback : int
        Maximum number of days to roll back before giving up

    Returns
    -------
    httpx.Response
        Response object with CSV content

    Raises
    ------
    BCBAPIError
        If unable to fetch after max rollback days exceeded
    """
    # Check if we've rolled back too far
    days_rolled_back = (date.today() - _date).days
    if days_rolled_back > max_rollback:
        raise BCBAPIError(
            f"No currency list available in last {max_rollback} days",
            status_code=503,  # Service Unavailable
        )

    url2 = f"https://www4.bcb.gov.br/Download/fechamento/M{_date:%Y%m%d}.csv"
    logger.debug(f"Fetching currency list from {url2}")
    try:
        res = get_client().get(url2)
    except httpx.HTTPError as ex:
        # Connection error: retry same date up to 3 times
        if n >= 3:
            raise_for_request_error(ex, context="Currency list")
        logger.warning(
            f"Connection error fetching {url2}, retrying (attempt {n + 1}/3)"
        )
        return _get_valid_currency_list(_date, n + 1, max_rollback)

    logger.debug(
        f"Currency list response: status={res.status_code}, length={len(res.content)}"
    )
    if res.status_code == 200:
        return res
    if res.status_code == 429 or res.status_code >= 500:
        raise_for_status(res, context="Currency list")

    # Non-200 response (file not found for date): roll back to previous day
    logger.debug(f"Currency list not found for {_date}, rolling back to previous day")
    return _get_valid_currency_list(_date - timedelta(1), 0, max_rollback)


def get_currency_list(
    cache: _ThreadSafeCache | None = None,
) -> pd.DataFrame:
    """Listagem com todas as moedas disponíveis na API e suas configurações de paridade.

    Parameters
    ----------
    cache : _ThreadSafeCache, optional
        Cache instance to use. If None, uses module-level default.

    Returns
    -------
    pd.DataFrame
        Tabela com a listagem de moedas disponíveis.

    Raises
    ------
    BCBAPIError
        If API returns error response
    """
    cache = cache or _DEFAULT_CACHE
    cache_key = _CacheKey(type="currency_list")
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    res = _get_valid_currency_list(date.today())
    df = pd.read_csv(StringIO(res.text), delimiter=";")
    df.columns = [
        "code",
        "name",
        "symbol",
        "country_code",
        "country_name",
        "type",
        "exclusion_date",
    ]
    df = df.loc[~df["country_code"].isna()]
    df["exclusion_date"] = pd.to_datetime(df["exclusion_date"], dayfirst=True)
    df["country_code"] = df["country_code"].astype("int32")
    df["code"] = df["code"].astype("int32")
    df["symbol"] = df["symbol"].str.strip()
    cache.set(cache_key, df)
    return df


def _get_currency_id(symbol: str) -> int:
    id_list = _currency_id_list()
    all_currencies = get_currency_list()
    x = pd.merge(id_list, all_currencies, on=["name"])
    matches = x.loc[x["symbol"] == symbol, "id"]
    if matches.empty:
        raise CurrencyNotFoundError(f"Unknown currency symbol: {symbol}")
    return int(matches.max())


def _raise_no_valid_currency_symbols(symbols: List[str]) -> NoReturn:
    requested = ", ".join(symbols) if symbols else "<empty>"
    raise CurrencyNotFoundError(f"No valid currency symbols found: {requested}")


def _is_html_response(response: httpx.Response) -> bool:
    content_type = response.headers.get("Content-Type", "").lower()
    if content_type.startswith("text/html"):
        return True
    body = response.content.lstrip().lower()
    return body.startswith((b"<!doctype html", b"<html", b"<body", b"<div"))


def _clean_currency_error_message(message: str) -> str:
    message = re.sub(r"^\W+", "", message)
    message = re.sub(r"\W+$", "", message)
    message = re.sub(r"\s+", " ", message)
    return message.strip()


def _extract_currency_html_error(content: bytes) -> str | None:
    try:
        doc = html.parse(BytesIO(content)).getroot()
    except (etree.ParserError, ValueError):
        return None
    xpath = "//div[@class='msgErro']"
    for element in doc.xpath(xpath):
        message = _clean_currency_error_message(str(element.text_content()))
        if message:
            return message
    return None


def _raise_currency_html_error(response: httpx.Response, symbol: str) -> NoReturn:
    message = _extract_currency_html_error(response.content)
    if message:
        raise BCBAPIError(
            f"BCB API returned error for {symbol}: {message}",
            status_code=400,
        )
    raise BCBAPIError(
        f"BCB API returned an HTML response for {symbol} "
        "without a recognized BCB error message",
        status_code=400,
    )


def _fetch_symbol_response(
    symbol: str, start_date: DateInput, end_date: DateInput
) -> "httpx.Response":
    """Fetch exchange rate CSV response for a symbol.

    Parameters
    ----------
    symbol : str
        Currency symbol (e.g., 'USD')
    start_date : DateInput
        Start date for the query
    end_date : DateInput
        End date for the query

    Returns
    -------
    httpx.Response
        Response object with CSV content

    Raises
    ------
    CurrencyNotFoundError
        If the currency symbol is not found
    BCBRateLimitError
        If API rate limit is exceeded (429)
    BCBAPIError
        If API returns other error status codes or HTML error page
    """
    cid = _get_currency_id(symbol)  # Raises CurrencyNotFoundError if not found
    url = _currency_url(cid, start_date, end_date)
    logger.debug(f"Fetching currency data for {symbol} from {url.split('?')[0]}")
    try:
        res = get_client().get(url)
    except httpx.HTTPError as ex:
        raise_for_request_error(ex, context=f"Currency data for {symbol}")
    logger.debug(
        f"Currency data response: status={res.status_code}, length={len(res.content)}"
    )

    # Handle HTML error responses (e.g., no data for date range).
    if _is_html_response(res):
        _raise_currency_html_error(res, symbol)

    raise_for_status(
        res,
        context=f"Currency data for {symbol}",
        not_found_message=f"Currency data not found for {symbol}",
    )

    return res


def _validate_currency_csv(csv_text: str) -> pd.DataFrame:
    """Parse and validate currency CSV format.

    Parameters
    ----------
    csv_text : str
        CSV content from BCB API

    Returns
    -------
    pd.DataFrame
        Parsed DataFrame with all columns

    Raises
    ------
    BCBAPIError
        If CSV format is invalid (wrong column count)
    """
    if not csv_text.strip():
        raise BCBAPIError("Currency CSV response is empty", status_code=400)
    try:
        df = pd.read_csv(StringIO(csv_text), delimiter=";", header=None, dtype=str)
    except (pd.errors.EmptyDataError, pd.errors.ParserError) as e:
        raise BCBAPIError(f"Failed to parse currency CSV: {e}", status_code=400) from e

    # Validate column count
    if len(df.columns) != 8:
        raise BCBAPIError(
            f"Invalid CSV format: expected 8 columns, got {len(df.columns)}",
            status_code=400,
        )

    # Assign meaningful names
    df.columns = ["Date", "_col1", "_col2", "_col3", "bid", "ask", "_col6", "_col7"]
    return df


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
    except (TypeError, ValueError) as e:
        raise BCBAPIError(
            f"Failed to parse currency date column: {str(e)}", status_code=400
        ) from e
    return df


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
        df["bid"] = df["bid"].str.replace(",", ".").astype(np.float64)
        df["ask"] = df["ask"].str.replace(",", ".").astype(np.float64)
    except (TypeError, ValueError) as e:
        raise BCBAPIError(
            f"Failed to parse currency numeric columns: {str(e)}", status_code=400
        ) from e
    return df


def _get_symbol(
    symbol: str, start_date: DateInput, end_date: DateInput
) -> pd.DataFrame:
    """Fetch and parse exchange rate data for a symbol.

    Parameters
    ----------
    symbol : str
        Currency symbol
    start_date : DateInput
        Start date
    end_date : DateInput
        End date

    Returns
    -------
    pd.DataFrame
        DataFrame with exchange rate data

    Raises
    ------
    CurrencyNotFoundError
        If currency not found
    BCBAPIError
        If API returns error or data format is invalid
    """
    res = _fetch_symbol_response(symbol, start_date, end_date)
    df = _validate_currency_csv(res.text)
    df = _parse_currency_dates(df)
    df = _parse_currency_types(df)
    df1 = df.set_index("Date")
    n = ["bid", "ask"]
    df1 = df1[n]
    tuples = list(zip([symbol] * len(n), n))
    df1.columns = pd.MultiIndex.from_tuples(tuples)
    return df1


def _get_symbol_text(symbol: str, start_date: DateInput, end_date: DateInput) -> str:
    """Fetch exchange rate data as CSV text for a symbol.

    Parameters
    ----------
    symbol : str
        Currency symbol
    start_date : DateInput
        Start date
    end_date : DateInput
        End date

    Returns
    -------
    str
        CSV text with exchange rate data

    Raises
    ------
    CurrencyNotFoundError
        If currency not found
    BCBAPIError
        If API returns error
    """
    res = _fetch_symbol_response(symbol, start_date, end_date)
    return res.text


# Type alias for text output with multiple symbols
CurrencyTextResult = Dict[str, str]  # Maps symbol → CSV text
CurrencySide = Literal["ask", "bid", "both"]
CurrencyGroupBy = Literal["symbol", "side"]
CurrencyOutput = Literal["dataframe", "text"]


def _normalize_currency_symbols(symbols: Union[str, List[str]]) -> List[str]:
    if isinstance(symbols, str):
        symbols = [symbols]
    if not symbols:
        raise ValueError("At least one currency symbol must be provided")
    for symbol in symbols:
        if not isinstance(symbol, str) or not symbol.strip():
            raise ValueError(f"Currency symbols must be non-empty strings: {symbol!r}")
    return symbols


def _validate_currency_query_inputs(
    symbols: Union[str, List[str]],
    start: DateInput,
    end: DateInput,
    side: str,
    groupby: str,
    output: str,
) -> List[str]:
    if output not in ("dataframe", "text"):
        raise ValueError("Unknown output value, use: dataframe, text")
    if side not in ("bid", "ask", "both"):
        raise ValueError("Unknown side value, use: bid, ask, both")
    if groupby not in ("symbol", "side"):
        raise ValueError("Unknown groupby value, use: symbol, side")
    Date(start)
    Date(end)
    return _normalize_currency_symbols(symbols)


@overload
def get(
    symbols: str,
    start: DateInput,
    end: DateInput,
    side: CurrencySide = ...,
    groupby: CurrencyGroupBy = ...,
    output: Literal["dataframe"] = ...,
) -> pd.DataFrame: ...


@overload
def get(
    symbols: List[str],
    start: DateInput,
    end: DateInput,
    side: CurrencySide = ...,
    groupby: CurrencyGroupBy = ...,
    output: Literal["dataframe"] = ...,
) -> pd.DataFrame: ...


@overload
def get(
    symbols: str,
    start: DateInput,
    end: DateInput,
    side: CurrencySide = ...,
    groupby: CurrencyGroupBy = ...,
    output: Literal["text"] = ...,
) -> str: ...


@overload
def get(
    symbols: List[str],
    start: DateInput,
    end: DateInput,
    side: CurrencySide = ...,
    groupby: CurrencyGroupBy = ...,
    output: Literal["text"] = ...,
) -> CurrencyTextResult: ...


def get(
    symbols: Union[str, List[str]],
    start: DateInput,
    end: DateInput,
    side: CurrencySide = "ask",
    groupby: CurrencyGroupBy = "symbol",
    output: CurrencyOutput = "dataframe",
) -> Union[pd.DataFrame, str, Dict[str, str]]:
    """
    Retorna um DataFrame pandas com séries temporais com taxas de câmbio.

    Parameters
    ----------

    symbols : str, List[str]
        Códigos das moedas padrão ISO. O código de uma única moeda que
        retorna uma série temporal univariada e uma lista de códigos
        retorna uma série temporal multivariada.
    start : str, int, date, datetime, Timestamp
        Data de início da série.
        Interpreta diferentes tipos e formatos de datas.
    end : string, int, date, datetime, Timestamp
        Data de início da série.
        Interpreta diferentes tipos e formatos de datas.
    side : {"ask", "bid", "both"}, default "ask"
        Define se a série retornada vem com os ``ask`` prices,
        ``bid`` prices ou ``both`` para ambos.
    groupby : {"symbol", "side"}, default "symbol"
        Define se os índices de coluna são agrupados por ``symbol`` ou
        por ``side``.
    output : {"dataframe", "text"}, default "dataframe"
        Define o formato de saída. Use ``"text"`` para retornar o CSV bruto.

    Returns
    -------

    Notes
    -----
    The currency ID list and the master currency table are cached in memory
    for the lifetime of the Python session so that multiple calls to
    :func:`get` do not repeat the same HTTP requests.  Use
    :func:`clear_cache` to invalidate the cache when fresh data is needed.

    DataFrame :
        Série temporal com cotações diárias das moedas solicitadas.
    """
    symbols = _validate_currency_query_inputs(
        symbols, start, end, side, groupby, output
    )

    if output == "text":
        results: Dict[str, str] = {}
        for symbol in symbols:
            try:
                raw = _get_symbol_text(symbol, start, end)
                results[symbol] = raw
            except CurrencyNotFoundError:
                pass  # Skip missing currencies
        if not results:
            _raise_no_valid_currency_symbols(symbols)
        if len(symbols) == 1:
            return results[symbols[0]]
        return results

    dss = []
    for symbol in symbols:
        try:
            df1 = _get_symbol(symbol, start, end)
            dss.append(df1)
        except CurrencyNotFoundError:
            pass  # Skip missing currencies
    if len(dss) > 0:
        df = pd.concat(dss, axis=1)
        if side in ("bid", "ask"):
            dx = df.reorder_levels([1, 0], axis=1).sort_index(axis=1)
            return dx[side]
        elif side == "both":
            if groupby == "symbol":
                return df
            elif groupby == "side":
                return df.reorder_levels([1, 0], axis=1).sort_index(axis=1)
            else:
                raise ValueError("Unknown groupby value, use: symbol, side")
        else:
            raise ValueError("Unknown side value, use: bid, ask, both")
    else:
        _raise_no_valid_currency_symbols(symbols)


async def _async_currency_id_list(
    cache: _ThreadSafeCache | None = None,
) -> pd.DataFrame:
    """Async version of _currency_id_list()."""
    cache = cache or _DEFAULT_CACHE
    cache_key = _CacheKey(type="currency_id_list")
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    url1 = (
        "https://ptax.bcb.gov.br/ptax_internet/consultaBoletim.do?"
        "method=exibeFormularioConsultaBoletim"
    )
    try:
        res = await get_async_client().get(url1)
    except httpx.HTTPError as ex:
        raise_for_request_error(ex, context="Currency ID list")
    raise_for_status(
        res,
        context="Currency ID list",
        not_found_message="BCB API endpoint not found (404)",
    )

    doc = html.parse(BytesIO(res.content)).getroot()
    xpath = "//select[@name='ChkMoeda']/option"
    x = [(elm.text, elm.get("value")) for elm in doc.xpath(xpath)]
    df = pd.DataFrame(x, columns=["name", "id"])
    df["id"] = df["id"].astype("int32")
    cache.set(cache_key, df)
    return df


async def _async_get_valid_currency_list(
    _date: date, n: int = 0, max_rollback: int = 30
) -> "httpx.Response":
    """Async version of _get_valid_currency_list()."""
    days_rolled_back = (date.today() - _date).days
    if days_rolled_back > max_rollback:
        raise BCBAPIError(
            f"No currency list available in last {max_rollback} days",
            status_code=503,
        )

    url2 = f"https://www4.bcb.gov.br/Download/fechamento/M{_date:%Y%m%d}.csv"
    try:
        res = await get_async_client().get(url2)
    except httpx.HTTPError as ex:
        if n >= 3:
            raise_for_request_error(ex, context="Currency list")
        return await _async_get_valid_currency_list(_date, n + 1, max_rollback)

    if res.status_code == 200:
        return res
    if res.status_code == 429 or res.status_code >= 500:
        raise_for_status(res, context="Currency list")
    return await _async_get_valid_currency_list(_date - timedelta(1), 0, max_rollback)


async def _async_get_currency_list(
    cache: _ThreadSafeCache | None = None,
) -> pd.DataFrame:
    """Async version of get_currency_list()."""
    cache = cache or _DEFAULT_CACHE
    cache_key = _CacheKey(type="currency_list")
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    res = await _async_get_valid_currency_list(date.today())
    df = pd.read_csv(StringIO(res.text), delimiter=";")
    df.columns = [
        "code",
        "name",
        "symbol",
        "country_code",
        "country_name",
        "type",
        "exclusion_date",
    ]
    df = df.loc[~df["country_code"].isna()]
    df["exclusion_date"] = pd.to_datetime(df["exclusion_date"], dayfirst=True)
    df["country_code"] = df["country_code"].astype("int32")
    df["code"] = df["code"].astype("int32")
    df["symbol"] = df["symbol"].str.strip()
    cache.set(cache_key, df)
    return df


async def _async_get_currency_id(symbol: str) -> int:
    """Async version of _get_currency_id() with concurrent cache warming."""
    id_list, all_currencies = await asyncio.gather(
        _async_currency_id_list(),
        _async_get_currency_list(),
    )
    x = pd.merge(id_list, all_currencies, on=["name"])
    matches = x.loc[x["symbol"] == symbol, "id"]
    if matches.empty:
        raise CurrencyNotFoundError(f"Unknown currency symbol: {symbol}")
    return int(matches.max())


async def _async_fetch_symbol_response(
    symbol: str, start_date: DateInput, end_date: DateInput
) -> "httpx.Response":
    """Async version of _fetch_symbol_response()."""
    cid = await _async_get_currency_id(symbol)
    url = _currency_url(cid, start_date, end_date)
    try:
        res = await get_async_client().get(url)
    except httpx.HTTPError as ex:
        raise_for_request_error(ex, context=f"Currency data for {symbol}")

    if _is_html_response(res):
        _raise_currency_html_error(res, symbol)

    raise_for_status(
        res,
        context=f"Currency data for {symbol}",
        not_found_message=f"Currency data not found for {symbol}",
    )

    return res


async def _async_get_symbol(
    symbol: str, start_date: DateInput, end_date: DateInput
) -> pd.DataFrame:
    """Async version of _get_symbol()."""
    res = await _async_fetch_symbol_response(symbol, start_date, end_date)
    df = _validate_currency_csv(res.text)
    df = _parse_currency_dates(df)
    df = _parse_currency_types(df)
    df1 = df.set_index("Date")
    n = ["bid", "ask"]
    df1 = df1[n]
    tuples = list(zip([symbol] * len(n), n))
    df1.columns = pd.MultiIndex.from_tuples(tuples)
    return df1


async def _async_get_symbol_text(
    symbol: str, start_date: DateInput, end_date: DateInput
) -> str:
    """Async version of _get_symbol_text()."""
    res = await _async_fetch_symbol_response(symbol, start_date, end_date)
    return res.text


async def async_get(
    symbols: Union[str, List[str]],
    start: DateInput,
    end: DateInput,
    side: CurrencySide = "ask",
    groupby: CurrencyGroupBy = "symbol",
    output: CurrencyOutput = "dataframe",
) -> Union[pd.DataFrame, str, Dict[str, str]]:
    """
    Retorna um DataFrame pandas com séries temporais com taxas de câmbio (async version).

    Uses :func:`asyncio.gather` to fetch multiple symbols concurrently.

    Same signature as :func:`get`, but returns a coroutine.

    Parameters
    ----------
    symbols : str, List[str]
        Códigos das moedas padrão ISO
    start : str, int, date, datetime, Timestamp
        Data de início da série
    end : string, int, date, datetime, Timestamp
        Data final da série
    side : {"ask", "bid", "both"}
        ``'ask'``, ``'bid'`` ou ``'both'``
    groupby : {"symbol", "side"}
        ``'symbol'`` ou ``'side'``
    output : {"dataframe", "text"}
        ``'dataframe'`` ou ``'text'``

    Returns
    -------
    Union[pd.DataFrame, str, Dict[str, str]]
        Série temporal conforme especificado
    """
    symbols = _validate_currency_query_inputs(
        symbols, start, end, side, groupby, output
    )

    if output == "text":
        results: Dict[str, str] = {}
        texts = await asyncio.gather(
            *[_async_get_symbol_text(symbol, start, end) for symbol in symbols],
            return_exceptions=True,
        )
        for symbol, text in zip(symbols, texts):
            if isinstance(text, CurrencyNotFoundError):
                continue
            if isinstance(text, BaseException):
                raise text
            results[symbol] = text
        if not results:
            _raise_no_valid_currency_symbols(symbols)
        if len(symbols) == 1:
            return results[symbols[0]]
        return results

    dss = await asyncio.gather(
        *[_async_get_symbol(symbol, start, end) for symbol in symbols],
        return_exceptions=True,
    )
    valid_dss = []
    for df in dss:
        if isinstance(df, CurrencyNotFoundError):
            continue
        if isinstance(df, BaseException):
            raise df
        valid_dss.append(df)

    if len(valid_dss) > 0:
        df = pd.concat(valid_dss, axis=1)
        if side in ("bid", "ask"):
            dx = df.reorder_levels([1, 0], axis=1).sort_index(axis=1)
            return dx[side]
        elif side == "both":
            if groupby == "symbol":
                return df
            elif groupby == "side":
                return df.reorder_levels([1, 0], axis=1).sort_index(axis=1)
            else:
                raise ValueError("Unknown groupby value, use: symbol, side")
        else:
            raise ValueError("Unknown side value, use: bid, ask, both")
    else:
        _raise_no_valid_currency_symbols(symbols)
