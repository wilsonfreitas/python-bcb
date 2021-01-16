
import sys
sys.path.append('.')
from datetime import datetime
import pandas as pd
from bcb import currency


def test_currency_id():
    assert currency.get_currency_id('USD') == 61


def test_currency_get_symbol():
    start_date = datetime.strptime('2020-12-01', '%Y-%m-%d')
    end_date = datetime.strptime('2020-12-05', '%Y-%m-%d')
    x = currency.get_symbol('USD', start_date, end_date)
    assert isinstance(x, pd.DataFrame)
    x = currency.get_symbol('ZAR', start_date, end_date)
    assert x is None
    x = currency.get('USD', start_date, end_date)
    assert isinstance(x, pd.DataFrame)
    x = currency.get('ZAR', start_date, end_date)
    assert x is None
    x = currency.get(['ZAR', 'ZZ1'], start_date, end_date)
    assert x is None
