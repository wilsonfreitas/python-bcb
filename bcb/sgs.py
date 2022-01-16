
from io import StringIO

import requests
import pandas as pd

from .utils import Date


class SGSCode:
    def __init__(self, code, name=None):
        if name is None:
            if isinstance(code, int) or isinstance(code, str):
                self.name = str(code)
                self.value = int(code)
        else:
            self.name = str(name)
            self.value = int(code)


def _codes(codes):
    if isinstance(codes, int) or isinstance(codes, str):
        yield SGSCode(codes)
    elif isinstance(codes, tuple):
        yield SGSCode(codes[1], codes[0])
    elif isinstance(codes, list):
        for cd in codes:
            _ist = isinstance(cd, tuple)
            yield SGSCode(cd[1], cd[0]) if _ist else SGSCode(cd)
    elif isinstance(codes, dict):
        for cd in codes:
            yield SGSCode(codes[cd], cd)


def _get_url_and_payload(code, start_date, end_date, last):
    payload = {'formato': 'json'}
    if last == 0:
        if start_date is not None or end_date is not None:
            payload['dataInicial'] = Date(start_date).date.strftime('%d/%m/%Y')
            end_date = end_date if end_date else 'today'
            payload['dataFinal'] = Date(end_date).date.strftime('%d/%m/%Y')
        url = 'http://api.bcb.gov.br/dados/serie/bcdata.sgs.{}/dados'\
            .format(code)
    else:
        url = ('http://api.bcb.gov.br/dados/serie/bcdata.sgs.{}/dados'
               '/ultimos/{}').format(code, last)

    return {
        'payload': payload,
        'url': url
    }


def _format_df(df, code, freq):
    cns = {'data': 'Date', 'valor': code.name, 'datafim': 'enddate'}
    df = df.rename(columns=cns)
    if 'Date' in df:
        df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y')
    if 'enddate' in df:
        df['enddate'] = pd.to_datetime(df['enddate'], format='%d/%m/%Y')
    df = df.set_index('Date')
    if freq:
        df.index = df.index.to_period(freq)
    return df


def get(codes, start=None, end=None, last=0, multi=True, freq=None):
    '''
    Retorna um DataFrame pandas com séries temporais obtidas do SGS.

    Parameters
    ----------

    symbols : {int, List[int], List[str], Dict[str:int]}
        Este argumento pode ser uma das opções:

        ``int`` : código da série temporal

        ``list`` ou ``tuple`` : lista ou tupla com pares ``('nome', código)``

        ``dict`` : dicionário com pares ``{'nome': código}``

        Com códigos numéricos é interessante utilizar os nomes com os códigos
        para definir os nomes nas colunas das séries temporais.
    start : str, int, date, datetime, Timestamp
        Data de início da série.
        Interpreta diferentes tipos e formatos de datas.
    end : string, int, date, datetime, Timestamp
        Data de início da série.
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
        quando solicitado mais de uma série.

    ``list`` :
        lista com séries temporais univariadas,
        quando solicitado mais de uma série.
    '''
    dfs = []
    for code in _codes(codes):
        urd = _get_url_and_payload(code.value, start, end, last)
        res = requests.get(urd['url'], params=urd['payload'])
        if res.status_code != 200:
            raise Exception('Download error: code = {}'.format(code.value))
        df = pd.read_json(StringIO(res.text))
        df = _format_df(df, code, freq)
        dfs.append(df)
    if len(dfs) == 1:
        return dfs[0]
    else:
        if multi:
            return pd.concat(dfs, axis=1)
        else:
            return dfs
