import re
from datetime import datetime

import pandas as pd
import pytest

from bcb import currency
from bcb.exceptions import CurrencyNotFoundError
from tests.conftest import (
    CURRENCY_LIST_JSON,
    CURRENCY_RATE_ODATA_JSON,
)

START = datetime(2020, 12, 1)
END = datetime(2020, 12, 7)

PTAX_MOEDAS_URL = re.compile(r".*olinda\.bcb\.gov\.br.*Moedas.*")
PTAX_RATE_ODATA_URL = re.compile(r".*olinda\.bcb\.gov\.br.*CotacaoMoedaPeriodo.*")


def add_currency_list_mock(httpx_mock):
    httpx_mock.add_response(
        url=PTAX_MOEDAS_URL,
        text=CURRENCY_LIST_JSON,
        status_code=200,
        headers={"Content-Type": "application/json"},
    )


def add_rate_mock(httpx_mock):
    httpx_mock.add_response(
        url=PTAX_RATE_ODATA_URL,
        text=CURRENCY_RATE_ODATA_JSON,
        status_code=200,
        headers={"Content-Type": "application/json"},
    )


# ---------------------------------------------------------------------------
# get_currency_list
# ---------------------------------------------------------------------------


def test_get_currency_list(httpx_mock):
    add_currency_list_mock(httpx_mock)
    df = currency.get_currency_list()
    assert isinstance(df, pd.DataFrame)
    assert "symbol" in df.columns
    assert "name" in df.columns
    assert "type" in df.columns
    assert "USD" in df["symbol"].values


def test_get_currency_list_cached(httpx_mock):
    add_currency_list_mock(httpx_mock)
    df1 = currency.get_currency_list()
    df2 = currency.get_currency_list()  # should use cache — no second HTTP call
    assert df1 is df2


def test_clear_cache(httpx_mock):
    # Populate the cache with one call
    add_currency_list_mock(httpx_mock)
    currency.get_currency_list()
    assert currency._CACHE  # cache is non-empty

    # clear_cache() empties it
    currency.clear_cache()
    assert not currency._CACHE

    # A subsequent call re-fetches and re-populates
    add_currency_list_mock(httpx_mock)
    currency.get_currency_list()
    assert currency._CACHE


# ---------------------------------------------------------------------------
# _validate_currency_symbol
# ---------------------------------------------------------------------------


def test_validate_currency_symbol_found(httpx_mock):
    add_currency_list_mock(httpx_mock)
    # Should not raise
    currency._validate_currency_symbol("USD")


def test_validate_currency_symbol_not_found(httpx_mock):
    add_currency_list_mock(httpx_mock)
    with pytest.raises(CurrencyNotFoundError, match="ZAR"):
        currency._validate_currency_symbol("ZAR")


# ---------------------------------------------------------------------------
# _get_symbol
# ---------------------------------------------------------------------------


def test_get_symbol_returns_dataframe(httpx_mock):
    add_currency_list_mock(httpx_mock)
    add_rate_mock(httpx_mock)
    df = currency._get_symbol("USD", START, END)
    assert df is not None
    assert isinstance(df, pd.DataFrame)
    assert ("USD", "bid") in df.columns
    assert ("USD", "ask") in df.columns
    assert len(df) == 5


def test_get_symbol_unknown_currency_returns_none(httpx_mock):
    add_currency_list_mock(httpx_mock)
    result = currency._get_symbol("ZAR", START, END)
    assert result is None


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


def test_currency_get_ask(httpx_mock):
    add_currency_list_mock(httpx_mock)
    add_rate_mock(httpx_mock)
    df = currency.get("USD", START, END, side="ask")
    assert isinstance(df, pd.DataFrame)
    assert "USD" in df.columns
    assert len(df) == 5


def test_currency_get_bid(httpx_mock):
    add_currency_list_mock(httpx_mock)
    add_rate_mock(httpx_mock)
    df = currency.get("USD", START, END, side="bid")
    assert isinstance(df, pd.DataFrame)
    assert "USD" in df.columns


def test_currency_get_both_symbol_groupby(httpx_mock):
    add_currency_list_mock(httpx_mock)
    add_rate_mock(httpx_mock)
    df = currency.get("USD", START, END, side="both", groupby="symbol")
    assert isinstance(df, pd.DataFrame)
    assert ("USD", "bid") in df.columns
    assert ("USD", "ask") in df.columns


def test_currency_get_both_side_groupby(httpx_mock):
    add_currency_list_mock(httpx_mock)
    add_rate_mock(httpx_mock)
    df = currency.get("USD", START, END, side="both", groupby="side")
    assert isinstance(df, pd.DataFrame)
    assert ("bid", "USD") in df.columns
    assert ("ask", "USD") in df.columns


def test_currency_get_invalid_side(httpx_mock):
    add_currency_list_mock(httpx_mock)
    add_rate_mock(httpx_mock)
    with pytest.raises(ValueError, match="Unknown side"):
        currency.get("USD", START, END, side="mid")


def test_currency_get_unknown_symbol_raises(httpx_mock):
    add_currency_list_mock(httpx_mock)
    with pytest.raises(CurrencyNotFoundError):
        currency.get("ZAR", START, END)


def test_currency_get_list_all_unknown_raises(httpx_mock):
    add_currency_list_mock(httpx_mock)
    with pytest.raises(CurrencyNotFoundError):
        currency.get(["ZAR", "ZZ1"], START, END)


# ---------------------------------------------------------------------------
# output="text" — raw JSON string
# ---------------------------------------------------------------------------


def test_currency_get_output_text_single_returns_string(httpx_mock):
    """get('USD', output='text') returns the raw JSON string."""
    add_currency_list_mock(httpx_mock)
    add_rate_mock(httpx_mock)
    result = currency.get("USD", START, END, output="text")
    assert isinstance(result, str)
    assert "2020-12-01" in result


def test_currency_get_output_text_multi_returns_dict(httpx_mock):
    """get(['USD', 'USD'], output='text') returns a dict mapping symbol → JSON."""
    add_currency_list_mock(httpx_mock)
    # Two calls for USD (same mock symbol, different entries in symbols list)
    httpx_mock.add_response(
        url=PTAX_RATE_ODATA_URL,
        text=CURRENCY_RATE_ODATA_JSON,
        status_code=200,
        headers={"Content-Type": "application/json"},
    )
    httpx_mock.add_response(
        url=PTAX_RATE_ODATA_URL,
        text=CURRENCY_RATE_ODATA_JSON,
        status_code=200,
        headers={"Content-Type": "application/json"},
    )
    result = currency.get(["USD", "USD"], START, END, output="text")
    assert isinstance(result, dict)
    assert "USD" in result
    assert isinstance(result["USD"], str)


def test_currency_get_output_text_unknown_raises(httpx_mock):
    """get('ZAR', output='text') raises CurrencyNotFoundError."""
    add_currency_list_mock(httpx_mock)
    with pytest.raises(CurrencyNotFoundError):
        currency.get("ZAR", START, END, output="text")


def test_currency_get_output_dataframe_is_default(httpx_mock):
    """Default output still returns DataFrame."""
    add_currency_list_mock(httpx_mock)
    add_rate_mock(httpx_mock)
    result = currency.get("USD", START, END)
    assert isinstance(result, pd.DataFrame)
