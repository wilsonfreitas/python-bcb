import re
from datetime import datetime

import pandas as pd
import pytest

from bcb import currency
from bcb.exceptions import CurrencyNotFoundError
from tests.conftest import (
    CURRENCY_ID_LIST_HTML,
    CURRENCY_LIST_CSV,
    CURRENCY_RATE_CSV,
)

START = datetime(2020, 12, 1)
END = datetime(2020, 12, 7)

PTAX_ID_LIST_URL = re.compile(r".*exibeFormularioConsultaBoletim.*")
PTAX_CSV_DOWNLOAD_URL = re.compile(r".*www4\.bcb\.gov\.br.*\.csv")
PTAX_RATE_URL = re.compile(r".*gerarCSVFechamento.*")


def add_id_list_mock(httpx_mock):
    httpx_mock.add_response(
        url=PTAX_ID_LIST_URL,
        content=CURRENCY_ID_LIST_HTML,
        status_code=200,
    )


def add_currency_list_mock(httpx_mock):
    httpx_mock.add_response(
        url=PTAX_CSV_DOWNLOAD_URL,
        text=CURRENCY_LIST_CSV,
        status_code=200,
    )


def add_rate_mock(httpx_mock):
    httpx_mock.add_response(
        url=PTAX_RATE_URL,
        text=CURRENCY_RATE_CSV,
        status_code=200,
        headers={"Content-Type": "text/csv"},
    )


# ---------------------------------------------------------------------------
# _currency_id_list
# ---------------------------------------------------------------------------


def test_currency_id_list(httpx_mock):
    add_id_list_mock(httpx_mock)
    df = currency._currency_id_list()
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["name", "id"]
    assert 61 in df["id"].values


def test_currency_id_list_cached(httpx_mock):
    add_id_list_mock(httpx_mock)
    df1 = currency._currency_id_list()
    df2 = currency._currency_id_list()  # should use cache — no second HTTP call
    assert df1 is df2


def test_clear_cache(httpx_mock):
    # Populate the cache with one call
    add_id_list_mock(httpx_mock)
    currency._currency_id_list()
    assert currency._CACHE  # cache is non-empty

    # clear_cache() empties it
    currency.clear_cache()
    assert not currency._CACHE

    # A subsequent call re-fetches and re-populates
    add_id_list_mock(httpx_mock)
    currency._currency_id_list()
    assert currency._CACHE


# ---------------------------------------------------------------------------
# get_currency_list
# ---------------------------------------------------------------------------


def test_get_currency_list(httpx_mock):
    add_currency_list_mock(httpx_mock)
    df = currency.get_currency_list()
    assert isinstance(df, pd.DataFrame)
    assert "symbol" in df.columns
    assert "USD" in df["symbol"].values
    assert df.loc[df["symbol"] == "USD", "code"].iloc[0] == 61


# ---------------------------------------------------------------------------
# _get_currency_id
# ---------------------------------------------------------------------------


def test_get_currency_id_found(httpx_mock):
    add_id_list_mock(httpx_mock)
    add_currency_list_mock(httpx_mock)
    assert currency._get_currency_id("USD") == 61


def test_get_currency_id_not_found(httpx_mock):
    add_id_list_mock(httpx_mock)
    add_currency_list_mock(httpx_mock)
    with pytest.raises(CurrencyNotFoundError, match="ZAR"):
        currency._get_currency_id("ZAR")


# ---------------------------------------------------------------------------
# _get_symbol
# ---------------------------------------------------------------------------


def test_get_symbol_returns_dataframe(httpx_mock):
    add_id_list_mock(httpx_mock)
    add_currency_list_mock(httpx_mock)
    add_rate_mock(httpx_mock)
    df = currency._get_symbol("USD", START, END)
    assert df is not None
    assert isinstance(df, pd.DataFrame)
    assert ("USD", "bid") in df.columns
    assert ("USD", "ask") in df.columns
    assert len(df) == 5


def test_get_symbol_unknown_currency_returns_none(httpx_mock):
    add_id_list_mock(httpx_mock)
    add_currency_list_mock(httpx_mock)
    result = currency._get_symbol("ZAR", START, END)
    assert result is None


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


def test_currency_get_ask(httpx_mock):
    add_id_list_mock(httpx_mock)
    add_currency_list_mock(httpx_mock)
    add_rate_mock(httpx_mock)
    df = currency.get("USD", START, END, side="ask")
    assert isinstance(df, pd.DataFrame)
    assert "USD" in df.columns
    assert len(df) == 5


def test_currency_get_bid(httpx_mock):
    add_id_list_mock(httpx_mock)
    add_currency_list_mock(httpx_mock)
    add_rate_mock(httpx_mock)
    df = currency.get("USD", START, END, side="bid")
    assert isinstance(df, pd.DataFrame)
    assert "USD" in df.columns


def test_currency_get_both_symbol_groupby(httpx_mock):
    add_id_list_mock(httpx_mock)
    add_currency_list_mock(httpx_mock)
    add_rate_mock(httpx_mock)
    df = currency.get("USD", START, END, side="both", groupby="symbol")
    assert isinstance(df, pd.DataFrame)
    assert ("USD", "bid") in df.columns
    assert ("USD", "ask") in df.columns


def test_currency_get_both_side_groupby(httpx_mock):
    add_id_list_mock(httpx_mock)
    add_currency_list_mock(httpx_mock)
    add_rate_mock(httpx_mock)
    df = currency.get("USD", START, END, side="both", groupby="side")
    assert isinstance(df, pd.DataFrame)
    assert ("bid", "USD") in df.columns
    assert ("ask", "USD") in df.columns


def test_currency_get_invalid_side(httpx_mock):
    add_id_list_mock(httpx_mock)
    add_currency_list_mock(httpx_mock)
    add_rate_mock(httpx_mock)
    with pytest.raises(ValueError, match="Unknown side"):
        currency.get("USD", START, END, side="mid")


def test_currency_get_unknown_symbol_raises(httpx_mock):
    add_id_list_mock(httpx_mock)
    add_currency_list_mock(httpx_mock)
    with pytest.raises(CurrencyNotFoundError):
        currency.get("ZAR", START, END)


def test_currency_get_list_all_unknown_raises(httpx_mock):
    add_id_list_mock(httpx_mock)
    add_currency_list_mock(httpx_mock)
    with pytest.raises(CurrencyNotFoundError):
        currency.get(["ZAR", "ZZ1"], START, END)
