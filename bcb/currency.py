import re
from datetime import date, timedelta
from io import BytesIO, StringIO
from typing import TYPE_CHECKING, Dict, List, Literal, Union, overload

import numpy as np
import pandas as pd
from lxml import html

from bcb.http import _CLIENT
from bcb.exceptions import (
    BCBAPIError,
    BCBAPINotFoundError,
    BCBRateLimitError,
    CurrencyNotFoundError,
)
from bcb.utils import Date, DateInput

if TYPE_CHECKING:
    import httpx

"""
O módulo :py:mod:`bcb.currency` tem como objetivo fazer consultas no site do conversor de moedas do BCB.
"""


def _currency_url(currency_id: int, start_date: DateInput, end_date: DateInput) -> str:
    start_date = Date(start_date)
    end_date = Date(end_date)
    return (
        f"https://ptax.bcb.gov.br/ptax_internet/consultaBoletim.do?"
        f"method=gerarCSVFechamentoMoedaNoPeriodo&"
        f"ChkMoeda={currency_id}&DATAINI={start_date.date:%d/%m/%Y}&DATAFIM={end_date.date:%d/%m/%Y}"
    )


_CACHE: dict[str, pd.DataFrame] = dict()


def clear_cache() -> None:
    """Clear the module-level session cache.

    :func:`get` and :func:`get_currency_list` cache the currency ID list and
    the full currency master table for the duration of the Python session so
    that repeated calls do not make redundant HTTP requests.  Call this
    function to force a fresh fetch on the next request (useful in tests or
    long-running scripts where the master data may have changed).
    """
    _CACHE.clear()


def _currency_id_list() -> pd.DataFrame:
    if _CACHE.get("TEMP_CURRENCY_ID_LIST") is not None:
        return _CACHE.get("TEMP_CURRENCY_ID_LIST")
    else:
        url1 = (
            "https://ptax.bcb.gov.br/ptax_internet/consultaBoletim.do?"
            "method=exibeFormularioConsultaBoletim"
        )
        res = _CLIENT.get(url1)
        if res.status_code == 429:
            raise BCBRateLimitError(
                "BCB API rate limit exceeded. Please try again later.",
                status_code=429,
            )
        if res.status_code == 404:
            raise BCBAPINotFoundError(
                "BCB API endpoint not found (404)",
                status_code=404,
            )
        if res.status_code >= 500:
            raise BCBAPIError(
                f"BCB API server error (status {res.status_code})",
                status_code=res.status_code,
            )
        if res.status_code != 200:
            msg = f"BCB API Request error, status code = {res.status_code}"
            raise BCBAPIError(msg, res.status_code)

        doc = html.parse(BytesIO(res.content)).getroot()
        xpath = "//select[@name='ChkMoeda']/option"
        x = [(elm.text, elm.get("value")) for elm in doc.xpath(xpath)]
        df = pd.DataFrame(x, columns=["name", "id"])
        df["id"] = df["id"].astype("int32")
        _CACHE["TEMP_CURRENCY_ID_LIST"] = df
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
    try:
        res = _CLIENT.get(url2)
    except Exception as ex:
        # Connection error: retry same date up to 3 times
        if n >= 3:
            raise ex
        return _get_valid_currency_list(_date, n + 1, max_rollback)

    if res.status_code == 200:
        return res
    else:
        # Non-200 response (file not found for date): roll back to previous day
        return _get_valid_currency_list(_date - timedelta(1), 0, max_rollback)


def get_currency_list() -> pd.DataFrame:
    """
    Listagem com todas as moedas disponíveis na API e suas configurações de paridade.

    Returns
    -------

    DataFrame :
        Tabela com a listagem de moedas disponíveis.
    """
    if _CACHE.get("TEMP_FILE_CURRENCY_LIST") is not None:
        return _CACHE.get("TEMP_FILE_CURRENCY_LIST")
    else:
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
        _CACHE["TEMP_FILE_CURRENCY_LIST"] = df
        return df


def _get_currency_id(symbol: str) -> int:
    id_list = _currency_id_list()
    all_currencies = get_currency_list()
    x = pd.merge(id_list, all_currencies, on=["name"])
    matches = x.loc[x["symbol"] == symbol, "id"]
    if matches.empty:
        raise CurrencyNotFoundError(f"Unknown currency symbol: {symbol}")
    return int(matches.max())


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
    res = _CLIENT.get(url)

    # Handle HTML error response (e.g., no data for date range)
    if res.headers["Content-Type"].startswith("text/html"):
        doc = html.parse(BytesIO(res.content)).getroot()
        xpath = "//div[@class='msgErro']"
        elm = doc.xpath(xpath)[0]
        x = elm.text
        x = re.sub(r"^\W+", "", x)
        x = re.sub(r"\W+$", "", x)
        msg = f"BCB API returned error: {x} - {symbol}"
        raise BCBAPIError(msg, status_code=400)

    # Handle HTTP error responses
    if res.status_code == 429:
        raise BCBRateLimitError(
            "BCB API rate limit exceeded. Please try again later.",
            status_code=429,
        )
    if res.status_code == 404:
        raise BCBAPINotFoundError(
            f"Currency data not found for {symbol}",
            status_code=404,
        )
    if res.status_code >= 500:
        raise BCBAPIError(
            f"BCB API server error (status {res.status_code})",
            status_code=res.status_code,
        )
    if res.status_code != 200:
        raise BCBAPIError(
            f"BCB API request failed with status {res.status_code}",
            status_code=res.status_code,
        )

    return res


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
        If API returns error
    """
    res = _fetch_symbol_response(symbol, start_date, end_date)
    columns = ["Date", "aa", "bb", "cc", "bid", "ask", "dd", "ee"]
    df = pd.read_csv(
        StringIO(res.text), delimiter=";", header=None, names=columns, dtype=str
    )
    df = df.assign(
        Date=lambda x: pd.to_datetime(x["Date"], format="%d%m%Y"),
        bid=lambda x: x["bid"].str.replace(",", ".").astype(np.float64),
        ask=lambda x: x["ask"].str.replace(",", ".").astype(np.float64),
    )
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


@overload
def get(
    symbols: Union[str, List[str]],
    start: DateInput,
    end: DateInput,
    side: str = ...,
    groupby: str = ...,
    output: Literal["dataframe"] = ...,
) -> pd.DataFrame: ...


@overload
def get(
    symbols: Union[str, List[str]],
    start: DateInput,
    end: DateInput,
    side: str = ...,
    groupby: str = ...,
    output: Literal["text"] = ...,
) -> Union[str, Dict[str, str]]: ...


def get(
    symbols: Union[str, List[str]],
    start: DateInput,
    end: DateInput,
    side: str = "ask",
    groupby: str = "symbol",
    output: str = "dataframe",
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
    side : str
        Define se a série retornada vem com os ``ask`` prices,
        ``bid`` prices ou ``both`` para ambos.
    groupby : str
        Define se os índices de coluna são agrupados por ``symbol`` ou
        por ``side``.

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
    if isinstance(symbols, str):
        symbols = [symbols]

    if output == "text":
        results: Dict[str, str] = {}
        for symbol in symbols:
            raw = _get_symbol_text(symbol, start, end)
            if raw is not None:
                results[symbol] = raw
        if not results:
            raise CurrencyNotFoundError(f"Currency not found: {symbols}")
        if len(symbols) == 1:
            return results[symbols[0]]
        return results

    dss = []
    for symbol in symbols:
        df1 = _get_symbol(symbol, start, end)
        if df1 is not None:
            dss.append(df1)
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
        raise CurrencyNotFoundError(f"Currency not found: {symbols}")
