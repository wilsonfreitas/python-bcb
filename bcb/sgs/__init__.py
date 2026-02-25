import json
from io import StringIO
from typing import Dict, Generator, List, Mapping, Optional, Tuple, TypeAlias, Union

import httpx
import pandas as pd

from bcb.exceptions import SGSError
from bcb.utils import Date, DateInput

"""
Sistema Gerenciador de Séries Temporais (SGS)

O módulo ``sgs`` obtem os dados do webservice do Banco Central,
interface json do serviço BCData/SGS -
`Sistema Gerenciador de Séries Temporais (SGS)
<https://www3.bcb.gov.br/sgspub/localizarseries/localizarSeries.do?method=prepararTelaLocalizarSeries>`_.
"""


class SGSCode:
    def __init__(self, code: Union[str, int], name: Optional[str] = None) -> None:
        if name is None:
            if isinstance(code, int) or isinstance(code, str):
                self.name = str(code)
                self.value = int(code)
        else:
            self.name = str(name)
            self.value = int(code)

    def __repr__(self) -> str:
        return f"{self.value} - {self.name}" if self.name else f"{self.value}"


SGSCodeInput: TypeAlias = Union[
    int,
    str,
    Tuple[str, Union[int, str]],
    List[Union[int, str, Tuple[str, Union[int, str]]]],
    Mapping[str, Union[int, str]],
]


def _codes(codes: SGSCodeInput) -> Generator[SGSCode, None, None]:
    if isinstance(codes, int) or isinstance(codes, str):
        yield SGSCode(codes)
    elif isinstance(codes, tuple):
        yield SGSCode(codes[1], codes[0])
    elif isinstance(codes, list):
        for cd in codes:
            if isinstance(cd, tuple):
                yield SGSCode(cd[1], cd[0])
            else:
                yield SGSCode(cd)
    elif isinstance(codes, Mapping):
        for name, code in codes.items():
            yield SGSCode(code, name)


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


def get(
    codes: SGSCodeInput,
    start: Optional[DateInput] = None,
    end: Optional[DateInput] = None,
    last: int = 0,
    multi: bool = True,
    freq: Optional[str] = None,
) -> Union[pd.DataFrame, List[pd.DataFrame]]:
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

    Returns
    -------

    ``DataFrame`` :
        série temporal univariada ou multivariada,
        quando solicitado mais de uma série (parâmetro ``multi=True``).

    ``list`` :
        lista com séries temporais univariadas,
        quando solicitado mais de uma série (parâmetro ``multi=False``).
    """
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
    res = httpx.get(url, params=payload, follow_redirects=True)
    if res.status_code != 200:
        try:
            res_json = json.loads(res.text)
        except Exception:
            res_json = {}
        if "error" in res_json:
            raise SGSError(f"BCB error: {res_json['error']}")
        elif "erro" in res_json:
            raise SGSError(f"BCB error: {res_json['erro']['detail']}")
        raise SGSError(f"Download error: code = {code}")
    return str(res.text)
