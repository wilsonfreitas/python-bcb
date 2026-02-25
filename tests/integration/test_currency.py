"""Integration tests for bcb.currency — require live BCB network access."""
from datetime import datetime, date

import pandas as pd
import pytest
from pytest import mark

from bcb import currency
from bcb.exceptions import CurrencyNotFoundError


@pytest.mark.integration
@mark.flaky(max_runs=20, min_passes=1)
def test_currency_id():
    assert currency._get_currency_id("USD") == 61


@pytest.mark.integration
@mark.flaky(max_runs=20, min_passes=1)
def test_currency_get_symbol():
    start_date = datetime.strptime("2020-12-01", "%Y-%m-%d")
    end_date = datetime.strptime("2020-12-05", "%Y-%m-%d")
    x = currency._get_symbol("USD", start_date, end_date)
    assert isinstance(x, pd.DataFrame)
    x = currency._get_symbol("ZAR", start_date, end_date)
    assert x is None
    x = currency.get("USD", start_date, end_date)
    assert isinstance(x, pd.DataFrame)
    with pytest.raises(CurrencyNotFoundError):
        currency.get("ZAR", start_date, end_date)
    with pytest.raises(CurrencyNotFoundError):
        currency.get(["ZAR", "ZZ1"], start_date, end_date)


@pytest.mark.integration
@mark.flaky(max_runs=20, min_passes=1)
def test_get_valid_currency_list():
    x = currency._get_valid_currency_list(date.today())
    assert x is not None
