
import re
import warnings
from io import BytesIO, StringIO
from datetime import datetime, date, timedelta

import requests
from lxml import html

import pandas as pd
import numpy as np

from .utils import Date


def currency_url(currency_id, start_date, end_date):
    start_date = Date(start_date)
    end_date = Date(end_date)
    url = ('https://ptax.bcb.gov.br/ptax_internet/consultaBoletim.do?'
           'method=gerarCSVFechamentoMoedaNoPeriodo&'
           'ChkMoeda={}&DATAINI={:%d/%m/%Y}&DATAFIM={:%d/%m/%Y}')
    return url.format(currency_id, start_date.date, end_date.date)


CACHE = dict()


def currency_id_list():
    if CACHE.get('TEMP_CURRENCY_ID_LIST') is not None:
        return CACHE.get('TEMP_CURRENCY_ID_LIST')
    else:
        url1 = ('https://ptax.bcb.gov.br/ptax_internet/consultaBoletim.do?'
                'method=exibeFormularioConsultaBoletim')
        res = requests.get(url1)
        if res.status_code != 200:
            msg = f'BCB API Request error, status code = {res.status_code}'
            raise Exception(msg)

        doc = html.parse(BytesIO(res.content)).getroot()
        xpath = "//select[@name='ChkMoeda']/option"
        x = [(elm.text, elm.get('value')) for elm in doc.xpath(xpath)]
        df = pd.DataFrame(x, columns=['name', 'id'])
        df['id'] = df['id'].astype('int32')
        CACHE['TEMP_CURRENCY_ID_LIST'] = df
        return df


def get_valid_currency_list(_date=date.today()):
    url2 = 'http://www4.bcb.gov.br/Download/fechamento/M{}.csv'
    url2 = url2.format(_date.strftime('%Y%m%d'))
    res = requests.get(url2)
    if res.status_code == 200:
        return res
    else:
        return get_valid_currency_list(_date - timedelta(1))


def get_currency_list():
    if CACHE.get('TEMP_FILE_CURRENCY_LIST') is not None:
        return CACHE.get('TEMP_FILE_CURRENCY_LIST')
    else:
        res = get_valid_currency_list()
        df = pd.read_csv(StringIO(res.text), delimiter=';')
        df.columns = ['code', 'name', 'symbol', 'country_code', 'country_name',
                      'type', 'exclusion_date']
        df = df.loc[~df['country_code'].isna()]
        df['exclusion_date'] = pd.to_datetime(df['exclusion_date'],
                                              dayfirst=True)
        df['country_code'] = df['country_code'].astype('int32')
        df['code'] = df['code'].astype('int32')
        df['symbol'] = df['symbol'].str.strip()
        CACHE['TEMP_FILE_CURRENCY_LIST'] = df
        return df


def get_currency_id(symbol):
    id_list = currency_id_list()
    all_currencies = get_currency_list()
    x = pd.merge(id_list, all_currencies, on=['name'])
    return np.max(x.loc[x['symbol'] == symbol, 'id'])


def get_symbol(symbol, start_date, end_date):
    cid = get_currency_id(symbol)
    url = currency_url(cid, start_date, end_date)
    res = requests.get(url)

    if res.headers['Content-Type'].startswith('text/html'):
        doc = html.parse(BytesIO(res.content)).getroot()
        xpath = "//div[@class='msgErro']"
        elm = doc.xpath(xpath)[0]
        x = elm.text
        x = re.sub(r'^\W+', '', x)
        x = re.sub(r'\W+$', '', x)
        msg = "BCB API returned error: {} - {}".format(x, symbol)
        warnings.warn(msg)
        return None

    columns = ['Date', 'aa', 'bb', 'cc', 'bid', 'ask', 'dd', 'ee']
    df = pd.read_csv(StringIO(res.text), delimiter=';', header=None,
                     names=columns, dtype=str)
    df = df.assign(
        Date=lambda x: pd.to_datetime(x['Date'], format='%d%m%Y'),
        bid=lambda x: x['bid'].str.replace(',', '.').astype(np.float64),
        ask=lambda x: x['ask'].str.replace(',', '.').astype(np.float64),
    )
    df1 = df.set_index('Date')
    n = ['bid', 'ask']
    df1 = df1[n]
    tuples = list(zip([symbol] * len(n), n))
    df1.columns = pd.MultiIndex.from_tuples(tuples)
    return df1


def get(symbols, start_date, end_date):
    if isinstance(symbols, str):
        symbols = [symbols]
    dss = []
    for symbol in symbols:
        df1 = get_symbol(symbol, start_date, end_date)
        if df1 is not None:
            dss.append(df1)
    if len(dss) > 0:
        return pd.concat(dss, axis=1)
    else:
        return None
