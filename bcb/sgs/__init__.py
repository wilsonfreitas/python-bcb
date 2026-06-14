from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from io import StringIO
from typing import (
    Dict,
    Generator,
    List,
    Literal,
    Mapping,
    Optional,
    Tuple,
    TypeAlias,
    Union,
    overload,
)

import httpx
import pandas as pd

from bcb.http import (
    get_async_client,
    get_client,
    raise_for_request_error,
    raise_for_status,
)
from bcb.exceptions import SGSError
from bcb.utils import Date, DateInput

logger = logging.getLogger(__name__)

"""
Sistema Gerenciador de Séries Temporais (SGS)

O módulo ``sgs`` obtem os dados do webservice do Banco Central,
interface json do serviço BCData/SGS -
`Sistema Gerenciador de Séries Temporais (SGS)
<https://www3.bcb.gov.br/sgspub/localizarseries/localizarSeries.do?method=prepararTelaLocalizarSeries>`_.
"""


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


SGSCodeInput: TypeAlias = Union[
    int,
    str,
    Tuple[str, Union[int, str]],
    List[Union[int, str, Tuple[str, Union[int, str]]]],
    Mapping[str, Union[int, str]],
]


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
        raise ValueError(f"SGS code must be positive integer, got {code.value}")


def _codes(codes: SGSCodeInput) -> Generator[SGSCode, None, None]:
    """Normalize various SGSCodeInput formats to SGSCode instances.

    Parameters
    ----------
    codes : SGSCodeInput
        Input in various formats: int, str, tuple, list, or mapping

    Yields
    ------
    SGSCode
        Validated SGSCode instances

    Raises
    ------
    ValueError
        If any code is a non-positive integer
    """
    if isinstance(codes, int) or isinstance(codes, str):
        code_obj = SGSCode.from_code(codes)
        _validate_sgs_code(code_obj)
        yield code_obj
    elif isinstance(codes, tuple):
        code_obj = SGSCode.from_named(codes[1], codes[0])
        _validate_sgs_code(code_obj)
        yield code_obj
    elif isinstance(codes, list):
        for cd in codes:
            if isinstance(cd, tuple):
                code_obj = SGSCode.from_named(cd[1], cd[0])
            else:
                code_obj = SGSCode.from_code(cd)
            _validate_sgs_code(code_obj)
            yield code_obj
    elif isinstance(codes, Mapping):
        for name, code in codes.items():
            code_obj = SGSCode.from_named(code, name)
            _validate_sgs_code(code_obj)
            yield code_obj


def _get_url_and_payload(
    code: int,
    start_date: Optional[DateInput],
    end_date: Optional[DateInput],
    last: int,
) -> Tuple[str, Dict[str, str]]:
    payload: Dict[str, str] = {"formato": "json"}
    if last == 0:
        if start_date is not None or end_date is not None:
            payload["dataInicial"] = Date(start_date).date.strftime("%d/%m/%Y")  # type: ignore[arg-type]
            end_date = end_date if end_date else "today"
            payload["dataFinal"] = Date(end_date).date.strftime("%d/%m/%Y")
        url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"
    else:
        url = (
            f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados/ultimos/{last}"
        )

    return url, payload


def _raise_sgs_response_error(res: httpx.Response, code: int) -> None:
    if res.status_code == 429:
        raise_for_status(res, context=f"SGS time series code={code}")

    try:
        res_json = json.loads(res.text)
    except json.JSONDecodeError:
        res_json = {}

    if "error" in res_json:
        raise SGSError(f"BCB error: {res_json['error']}")
    if "erro" in res_json:
        raise SGSError(f"BCB error: {res_json['erro']['detail']}")

    raise_for_status(
        res,
        context=f"SGS time series code={code}",
        error_cls=SGSError,
        not_found_cls=SGSError,
        server_error_cls=SGSError,
        error_message=f"Download error: code = {code}",
    )


def _format_df(df: pd.DataFrame, code: SGSCode, freq: Optional[str]) -> pd.DataFrame:
    cns = {"data": "Date", "valor": code.name, "datafim": "enddate"}
    df = df.rename(columns=cns)
    if "Date" in df:
        df["Date"] = pd.to_datetime(df["Date"], format="%d/%m/%Y")
    if "enddate" in df:
        df["enddate"] = pd.to_datetime(df["enddate"], format="%d/%m/%Y")
    df = df.set_index("Date")
    if freq:
        df.index = df.index.to_period(freq)
    return df


@overload
def get(
    codes: SGSCodeInput,
    start: Optional[DateInput] = ...,
    end: Optional[DateInput] = ...,
    last: int = ...,
    multi: bool = ...,
    freq: Optional[str] = ...,
    output: Literal["dataframe"] = ...,
) -> Union[pd.DataFrame, List[pd.DataFrame]]: ...


@overload
def get(
    codes: SGSCodeInput,
    start: Optional[DateInput] = ...,
    end: Optional[DateInput] = ...,
    last: int = ...,
    multi: bool = ...,
    freq: Optional[str] = ...,
    output: Literal["text"] = ...,
) -> Union[str, Dict[int, str]]: ...


def get(
    codes: SGSCodeInput,
    start: Optional[DateInput] = None,
    end: Optional[DateInput] = None,
    last: int = 0,
    multi: bool = True,
    freq: Optional[str] = None,
    output: str = "dataframe",
) -> Union[pd.DataFrame, List[pd.DataFrame], str, Dict[int, str]]:
    """
    Retorna um DataFrame pandas com séries temporais obtidas do SGS.

    Parameters
    ----------

    codes : {int, List[int], List[str], Dict[str:int]}
        Este argumento pode ser uma das opções:

        * ``int`` : código da série temporal
        * ``list`` ou ``tuple`` : lista ou tupla com códigos
        * ``list`` ou ``tuple`` : lista ou tupla com pares ``('nome', código)``
        * ``dict`` : dicionário com pares ``{'nome': código}``

        Com códigos numéricos é interessante utilizar os nomes com os códigos
        para definir os nomes nas colunas das séries temporais.
    start : str, int, date, datetime, Timestamp
        Data de início da série.
        Interpreta diferentes tipos e formatos de datas.
    end : string, int, date, datetime, Timestamp
        Data final da série.
        Interpreta diferentes tipos e formatos de datas.
    last : int
        Retorna os últimos ``last`` elementos disponíveis da série temporal
        solicitada. Se ``last`` for maior que 0 (zero) os argumentos ``start``
        e ``end`` são ignorados.
    multi : bool
        Define se, quando mais de 1 série for solicitada, a função retorna uma
        série multivariada ou uma lista com séries univariadas.
    freq : str
        Define a frequência a ser utilizada na série temporal
    output : str
        Define o formato de saída. Use ``'dataframe'`` (padrão) para retornar
        um DataFrame pandas, ou ``'text'`` para retornar o JSON bruto da API
        do BCB. Para um único código retorna uma string; para múltiplos
        códigos retorna um ``dict`` mapeando código inteiro → JSON string.

    Returns
    -------

    ``DataFrame`` :
        série temporal univariada ou multivariada,
        quando solicitado mais de uma série (parâmetro ``multi=True``).

    ``list`` :
        lista com séries temporais univariadas,
        quando solicitado mais de uma série (parâmetro ``multi=False``).

    ``str`` :
        JSON bruto da API (quando ``output='text'`` e um único código).

    ``dict`` :
        Mapeamento de código → JSON bruto (quando ``output='text'`` e
        múltiplos códigos).
    """
    if output == "text":
        results: Dict[int, str] = {}
        for code in _codes(codes):
            results[code.value] = get_json(code.value, start, end, last)
        values = list(results.values())
        if len(values) == 1:
            return values[0]
        return results

    dfs = []
    for code in _codes(codes):
        text = get_json(code.value, start, end, last)
        df = pd.read_json(StringIO(text))
        df = _format_df(df, code, freq)
        dfs.append(df)
    if len(dfs) == 1:
        return dfs[0]
    else:
        if multi:
            return pd.concat(dfs, axis=1)
        else:
            return dfs


def get_json(
    code: int,
    start: Optional[DateInput] = None,
    end: Optional[DateInput] = None,
    last: int = 0,
) -> str:
    """
    Retorna um JSON com séries temporais obtidas do SGS.

    Parameters
    ----------

    code : int
        Código da série temporal
    start : str, int, date, datetime, Timestamp
        Data de início da série.
        Interpreta diferentes tipos e formatos de datas.
    end : string, int, date, datetime, Timestamp
        Data final da série.
        Interpreta diferentes tipos e formatos de datas.
    last : int
        Retorna os últimos ``last`` elementos disponíveis da série temporal
        solicitada. Se ``last`` for maior que 0 (zero) os argumentos ``start``
        e ``end`` são ignorados.

    Returns
    -------

    JSON :
        série temporal univariada em formato JSON.
    """
    url, payload = _get_url_and_payload(code, start, end, last)
    logger.debug(f"Fetching SGS time series code={code} from {url.split('/dados')[0]}")
    try:
        res = get_client().get(url, params=payload)
    except httpx.HTTPError as ex:
        raise_for_request_error(
            ex, context=f"SGS time series code={code}", error_cls=SGSError
        )
    logger.debug(f"SGS response: status={res.status_code}, length={len(res.text)}")

    if res.status_code != 200:
        _raise_sgs_response_error(res, code)
    return str(res.text)


async def async_get_json(
    code: int,
    start: Optional[DateInput] = None,
    end: Optional[DateInput] = None,
    last: int = 0,
) -> str:
    """
    Retorna um JSON com séries temporais obtidas do SGS (async version).

    Parameters
    ----------
    code : int
        Código da série temporal
    start : str, int, date, datetime, Timestamp, optional
        Data de início da série
    end : string, int, date, datetime, Timestamp, optional
        Data final da série
    last : int
        Retorna os últimos ``last`` elementos disponíveis

    Returns
    -------
    str
        JSON bruto da API do BCB

    Raises
    ------
    BCBRateLimitError
        Se API rate limit é excedido (429)
    SGSError
        Se a API retorna um erro
    """
    url, payload = _get_url_and_payload(code, start, end, last)
    logger.debug(
        f"Fetching SGS time series (async) code={code} from {url.split('/dados')[0]}"
    )
    try:
        res = await get_async_client().get(url, params=payload)
    except httpx.HTTPError as ex:
        raise_for_request_error(
            ex, context=f"SGS time series code={code}", error_cls=SGSError
        )
    logger.debug(
        f"SGS (async) response: status={res.status_code}, length={len(res.text)}"
    )

    if res.status_code != 200:
        _raise_sgs_response_error(res, code)
    return str(res.text)


async def async_get(
    codes: SGSCodeInput,
    start: Optional[DateInput] = None,
    end: Optional[DateInput] = None,
    last: int = 0,
    multi: bool = True,
    freq: Optional[str] = None,
    output: str = "dataframe",
) -> Union[pd.DataFrame, List[pd.DataFrame], str, Dict[int, str]]:
    """
    Retorna um DataFrame pandas com séries temporais obtidas do SGS (async version).

    Same signature as :func:`get`, but uses async HTTP requests and
    :func:`asyncio.gather` to fetch multiple codes concurrently.

    Parameters
    ----------
    codes : {int, List[int], List[str], Dict[str:int]}
        Código(s) da série temporal
    start : str, int, date, datetime, Timestamp, optional
        Data de início da série
    end : string, int, date, datetime, Timestamp, optional
        Data final da série
    last : int
        Retorna os últimos ``last`` elementos disponíveis
    multi : bool
        Define se retorna série multivariada ou lista de séries univariadas
    freq : str, optional
        Frequência a ser utilizada na série temporal
    output : str
        Formato de saída: ``'dataframe'`` ou ``'text'``

    Returns
    -------
    Union[pd.DataFrame, List[pd.DataFrame], str, Dict[int, str]]
        Série(s) temporal(is) conforme especificado
    """
    code_list = list(_codes(codes))

    # Concurrent HTTP requests via asyncio.gather()
    texts = await asyncio.gather(
        *[async_get_json(c.value, start, end, last) for c in code_list]
    )

    if output == "text":
        results: Dict[int, str] = {c.value: t for c, t in zip(code_list, texts)}
        values = list(results.values())
        if len(values) == 1:
            return values[0]
        return results

    dfs = [
        _format_df(pd.read_json(StringIO(t)), c, freq) for c, t in zip(code_list, texts)
    ]
    if len(dfs) == 1:
        return dfs[0]
    else:
        if multi:
            return pd.concat(dfs, axis=1)
        else:
            return dfs
