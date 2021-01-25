
from datetime import datetime
import warnings
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


def format_df(df, code):
    cns = {'data': 'date', 'valor': code.name, 'datafim': 'end_date'}
    df = df.rename(columns=cns)
    if 'date' in df:
        df['date'] = pd.to_datetime(df['date'], format='%d/%m/%Y')
    if 'end_date' in df:
        df['end_date'] = pd.to_datetime(df['end_date'], format='%d/%m/%Y')
    df = df.set_index('date')
    return df


def get(codes, start_date=None, end_date=None, last=0):
    dfs = []
    for code in _codes(codes):
        urd = _get_url_and_payload(code.value, start_date, end_date, last)
        res = requests.get(urd['url'], params=urd['payload'])
        if res.status_code != 200:
            raise Exception('Download error: code = {}'.format(code.value))
        df = pd.read_json(StringIO(res.text))
        df = format_df(df, code)
        dfs.append(df)
    if len(dfs) == 1:
        return dfs[0]
    else:
        return dfs
