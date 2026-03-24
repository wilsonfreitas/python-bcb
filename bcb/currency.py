from typing import Dict, List, Literal, Optional, Union, overload

import httpx
import pandas as pd

from .exceptions import BCBAPIError, CurrencyNotFoundError
from .utils import Date, DateInput

"""
O módulo :py:mod:`bcb.currency` tem como objetivo fazer consultas no site do conversor de moedas do BCB.
"""

_PTAX_BASE_URL = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata"

_CACHE: dict[str, pd.DataFrame] = dict()


def clear_cache() -> None:
    """Clear the module-level session cache.

    :func:`get` and :func:`get_currency_list` cache the currency list for the
    duration of the Python session so that repeated calls do not make redundant
    HTTP requests.  Call this function to force a fresh fetch on the next
    request (useful in tests or long-running scripts where the data may have
    changed).
    """
    _CACHE.clear()


def get_currency_list() -> pd.DataFrame:
    """
    Listagem com todas as moedas disponíveis na API e suas configurações de paridade.

    Returns
    -------

    DataFrame :
        Tabela com a listagem de moedas disponíveis (colunas: ``symbol``,
        ``name``, ``type``).
    """
    cached = _CACHE.get("TEMP_FILE_CURRENCY_LIST")
    if cached is not None:
        return cached
    url = f"{_PTAX_BASE_URL}/Moedas?$format=json"
    res = httpx.get(url, follow_redirects=True)
    if res.status_code != 200:
        msg = f"BCB API Request error, status code = {res.status_code}"
        raise BCBAPIError(msg, res.status_code)
    data = res.json()
    df = pd.DataFrame(data["value"])
    df = df.rename(
        columns={"simbolo": "symbol", "nomeFormatado": "name", "tipoMoeda": "type"}
    )
    _CACHE["TEMP_FILE_CURRENCY_LIST"] = df
    return df


def _validate_currency_symbol(symbol: str) -> None:
    all_currencies = get_currency_list()
    if symbol not in all_currencies["symbol"].values:
        raise CurrencyNotFoundError(f"Unknown currency symbol: {symbol}")


def _currency_url(symbol: str, start_date: DateInput, end_date: DateInput) -> str:
    start_date = Date(start_date)
    end_date = Date(end_date)
    return (
        f"{_PTAX_BASE_URL}/CotacaoMoedaPeriodo("
        f"moeda=@moeda,dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)?"
        f"@moeda='{symbol}'&"
        f"@dataInicial='{start_date.date:%m-%d-%Y}'&"
        f"@dataFinalCotacao='{end_date.date:%m-%d-%Y}'&"
        f"$format=json"
    )


def _fetch_symbol_response(
    symbol: str, start_date: DateInput, end_date: DateInput
) -> Optional[httpx.Response]:
    try:
        _validate_currency_symbol(symbol)
    except CurrencyNotFoundError:
        return None
    url = _currency_url(symbol, start_date, end_date)
    res = httpx.get(url, follow_redirects=True)
    if res.status_code != 200:
        return None
    return res


def _get_symbol(
    symbol: str, start_date: DateInput, end_date: DateInput
) -> Optional[pd.DataFrame]:
    res = _fetch_symbol_response(symbol, start_date, end_date)
    if res is None:
        return None
    data = res.json()
    if not data.get("value"):
        return None
    df = pd.DataFrame(data["value"])
    df = df[df["tipoBoletim"] == "Fechamento"].copy()
    if df.empty:
        return None
    df["Date"] = pd.to_datetime(df["dataHoraCotacao"]).dt.normalize()
    df = df.rename(columns={"cotacaoCompra": "bid", "cotacaoVenda": "ask"})
    n = ["bid", "ask"]
    df1 = df.set_index("Date")[n]
    tuples = list(zip([symbol] * len(n), n))
    df1.columns = pd.MultiIndex.from_tuples(tuples)
    return df1


def _get_symbol_text(
    symbol: str, start_date: DateInput, end_date: DateInput
) -> Optional[str]:
    res = _fetch_symbol_response(symbol, start_date, end_date)
    return res.text if res is not None else None


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
