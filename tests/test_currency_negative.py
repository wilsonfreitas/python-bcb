"""Negative test cases for bcb.currency module.

Tests for error handling, malformed data, and edge cases.
"""

import re
from datetime import date, datetime, timedelta

import httpx
import pandas as pd
import pytest

from bcb import currency
from bcb.exceptions import BCBAPIError, CurrencyNotFoundError

START = datetime(2020, 12, 1)
END = datetime(2020, 12, 7)

PTAX_ID_LIST_URL = re.compile(r".*exibeFormularioConsultaBoletim.*")
PTAX_CSV_DOWNLOAD_URL = re.compile(r".*www4\.bcb\.gov\.br.*\.csv")
PTAX_RATE_URL = re.compile(r".*gerarCSVFechamento.*")


# ---------------------------------------------------------------------------
# 404 and 429 API response errors
# ---------------------------------------------------------------------------


def test_get_currency_id_list_404_raises(httpx_mock):
    """Test that 404 response raises BCBAPINotFoundError."""
    httpx_mock.add_response(
        url=PTAX_ID_LIST_URL,
        status_code=404,
    )
    with pytest.raises(BCBAPIError):
        currency._currency_id_list()


def test_get_currency_id_list_429_rate_limit_raises(httpx_mock):
    """Test that 429 response raises BCBRateLimitError."""
    from bcb.exceptions import BCBRateLimitError

    httpx_mock.add_response(
        url=PTAX_ID_LIST_URL,
        status_code=429,
    )
    with pytest.raises(BCBRateLimitError):
        currency._currency_id_list()


def test_get_currency_id_list_500_raises(httpx_mock):
    """Test that 500 response raises BCBAPIError."""
    httpx_mock.add_response(
        url=PTAX_ID_LIST_URL,
        status_code=500,
    )
    with pytest.raises(BCBAPIError):
        currency._currency_id_list()


def test_get_currency_id_list_connection_error_raises(httpx_mock):
    httpx_mock.add_exception(
        httpx.ConnectError("network down"),
        url=PTAX_ID_LIST_URL,
    )

    with pytest.raises(BCBAPIError, match="Currency ID list"):
        currency._currency_id_list()


def test_fetch_symbol_timeout_error_raises(httpx_mock):
    from tests.conftest import CURRENCY_ID_LIST_HTML, CURRENCY_LIST_CSV

    httpx_mock.add_response(
        url=PTAX_ID_LIST_URL,
        content=CURRENCY_ID_LIST_HTML,
        status_code=200,
    )
    httpx_mock.add_response(
        url=PTAX_CSV_DOWNLOAD_URL,
        text=CURRENCY_LIST_CSV,
        status_code=200,
    )
    httpx_mock.add_exception(
        httpx.TimeoutException("request timed out"),
        url=PTAX_RATE_URL,
    )

    with pytest.raises(BCBAPIError, match="Currency data for USD"):
        currency._fetch_symbol_response("USD", START, END)


def test_fetch_symbol_404_raises(httpx_mock):
    """Test that 404 when fetching rates raises BCBAPINotFoundError."""
    from tests.conftest import CURRENCY_ID_LIST_HTML, CURRENCY_LIST_CSV

    httpx_mock.add_response(
        url=re.compile(r".*exibeFormularioConsultaBoletim.*"),
        content=CURRENCY_ID_LIST_HTML,
        status_code=200,
    )
    httpx_mock.add_response(
        url=re.compile(r".*www4\.bcb\.gov\.br.*\.csv"),
        text=CURRENCY_LIST_CSV,
        status_code=200,
    )
    httpx_mock.add_response(
        url=PTAX_RATE_URL,
        text="",
        status_code=404,
        headers={"Content-Type": "text/plain"},
    )
    with pytest.raises(BCBAPIError):
        currency._fetch_symbol_response("USD", START, END)


def test_fetch_symbol_429_rate_limit_raises(httpx_mock):
    """Test that 429 when fetching rates raises BCBRateLimitError."""
    from bcb.exceptions import BCBRateLimitError
    from tests.conftest import CURRENCY_ID_LIST_HTML, CURRENCY_LIST_CSV

    httpx_mock.add_response(
        url=re.compile(r".*exibeFormularioConsultaBoletim.*"),
        content=CURRENCY_ID_LIST_HTML,
        status_code=200,
    )
    httpx_mock.add_response(
        url=re.compile(r".*www4\.bcb\.gov\.br.*\.csv"),
        text=CURRENCY_LIST_CSV,
        status_code=200,
    )
    httpx_mock.add_response(
        url=PTAX_RATE_URL,
        text="",
        status_code=429,
        headers={"Content-Type": "text/plain"},
    )
    with pytest.raises(BCBRateLimitError):
        currency._fetch_symbol_response("USD", START, END)


# ---------------------------------------------------------------------------
# Malformed data (CSV/HTML)
# ---------------------------------------------------------------------------


def test_fetch_symbol_html_error_extracts_message(httpx_mock):
    """HTML error pages with the expected element raise BCBAPIError."""
    from tests.conftest import CURRENCY_ID_LIST_HTML, CURRENCY_LIST_CSV

    httpx_mock.add_response(
        url=PTAX_ID_LIST_URL,
        content=CURRENCY_ID_LIST_HTML,
        status_code=200,
    )
    httpx_mock.add_response(
        url=PTAX_CSV_DOWNLOAD_URL,
        text=CURRENCY_LIST_CSV,
        status_code=200,
    )
    httpx_mock.add_response(
        url=PTAX_RATE_URL,
        text="<html><body><div class='msgErro'> No data available </div></body></html>",
        status_code=200,
        headers={"Content-Type": "text/html"},
    )

    with pytest.raises(BCBAPIError, match="No data available"):
        currency._fetch_symbol_response("USD", START, END)


def test_fetch_symbol_unexpected_html_without_content_type_raises(httpx_mock):
    """HTML bodies without Content-Type or msgErro still raise BCBAPIError."""
    from tests.conftest import CURRENCY_ID_LIST_HTML, CURRENCY_LIST_CSV

    httpx_mock.add_response(
        url=PTAX_ID_LIST_URL,
        content=CURRENCY_ID_LIST_HTML,
        status_code=200,
    )
    httpx_mock.add_response(
        url=PTAX_CSV_DOWNLOAD_URL,
        text=CURRENCY_LIST_CSV,
        status_code=200,
    )
    httpx_mock.add_response(
        url=PTAX_RATE_URL,
        text="<html><body><p>temporary failure</p></body></html>",
        status_code=200,
        headers={},
    )

    with pytest.raises(BCBAPIError, match="HTML response.*USD.*recognized"):
        currency._fetch_symbol_response("USD", START, END)


def test_get_symbol_missing_content_type_valid_csv_parses(httpx_mock):
    """Missing Content-Type alone does not reject a valid CSV response."""
    from tests.conftest import (
        CURRENCY_ID_LIST_HTML,
        CURRENCY_LIST_CSV,
        CURRENCY_RATE_CSV,
    )

    httpx_mock.add_response(
        url=PTAX_ID_LIST_URL,
        content=CURRENCY_ID_LIST_HTML,
        status_code=200,
    )
    httpx_mock.add_response(
        url=PTAX_CSV_DOWNLOAD_URL,
        text=CURRENCY_LIST_CSV,
        status_code=200,
    )
    httpx_mock.add_response(
        url=PTAX_RATE_URL,
        text=CURRENCY_RATE_CSV,
        status_code=200,
        headers={},
    )

    df = currency._get_symbol("USD", START, END)

    assert ("USD", "bid") in df.columns


def test_get_symbol_empty_response_body_raises(httpx_mock):
    """Empty CSV responses raise BCBAPIError."""
    from tests.conftest import CURRENCY_ID_LIST_HTML, CURRENCY_LIST_CSV

    httpx_mock.add_response(
        url=PTAX_ID_LIST_URL,
        content=CURRENCY_ID_LIST_HTML,
        status_code=200,
    )
    httpx_mock.add_response(
        url=PTAX_CSV_DOWNLOAD_URL,
        text=CURRENCY_LIST_CSV,
        status_code=200,
    )
    httpx_mock.add_response(
        url=PTAX_RATE_URL,
        text="",
        status_code=200,
        headers={"Content-Type": "text/csv"},
    )

    with pytest.raises(BCBAPIError, match="empty"):
        currency._get_symbol("USD", START, END)


def test_get_symbol_malformed_csv_wrong_column_count_raises(httpx_mock):
    """Test that CSV with wrong column count raises BCBAPIError."""
    from tests.conftest import CURRENCY_ID_LIST_HTML, CURRENCY_LIST_CSV

    httpx_mock.add_response(
        url=PTAX_ID_LIST_URL,
        content=CURRENCY_ID_LIST_HTML,
        status_code=200,
    )
    httpx_mock.add_response(
        url=PTAX_CSV_DOWNLOAD_URL,
        text=CURRENCY_LIST_CSV,
        status_code=200,
    )
    # CSV with only 7 columns instead of 8
    malformed_csv = "01122020;0;0;0;5.0000;5.1000;0\n"
    httpx_mock.add_response(
        url=PTAX_RATE_URL,
        text=malformed_csv,
        status_code=200,
    )
    with pytest.raises(BCBAPIError, match="8 columns"):
        currency._get_symbol("USD", START, END)


def test_get_symbol_malformed_csv_invalid_date_format_raises(httpx_mock):
    """Test that CSV with invalid date format raises BCBAPIError."""
    from tests.conftest import CURRENCY_ID_LIST_HTML, CURRENCY_LIST_CSV

    httpx_mock.add_response(
        url=PTAX_ID_LIST_URL,
        content=CURRENCY_ID_LIST_HTML,
        status_code=200,
    )
    httpx_mock.add_response(
        url=PTAX_CSV_DOWNLOAD_URL,
        text=CURRENCY_LIST_CSV,
        status_code=200,
    )
    # CSV with invalid date format (YYYY-MM-DD instead of DDMMYYYY)
    malformed_csv = "2020-12-01;0;0;0;5.0000;5.1000;0;0\n"
    httpx_mock.add_response(
        url=PTAX_RATE_URL,
        text=malformed_csv,
        status_code=200,
    )
    with pytest.raises(BCBAPIError, match="date column"):
        currency._get_symbol("USD", START, END)


def test_get_symbol_malformed_csv_invalid_numeric_conversion_raises(httpx_mock):
    """Test that CSV with non-numeric bid/ask raises BCBAPIError."""
    from tests.conftest import CURRENCY_ID_LIST_HTML, CURRENCY_LIST_CSV

    httpx_mock.add_response(
        url=PTAX_ID_LIST_URL,
        content=CURRENCY_ID_LIST_HTML,
        status_code=200,
    )
    httpx_mock.add_response(
        url=PTAX_CSV_DOWNLOAD_URL,
        text=CURRENCY_LIST_CSV,
        status_code=200,
    )
    # CSV with non-numeric bid/ask values
    malformed_csv = "01122020;0;0;0;INVALID;INVALID;0;0\n"
    httpx_mock.add_response(
        url=PTAX_RATE_URL,
        text=malformed_csv,
        status_code=200,
    )
    with pytest.raises(BCBAPIError, match="numeric columns"):
        currency._get_symbol("USD", START, END)


# ---------------------------------------------------------------------------
# Invalid input handling
# ---------------------------------------------------------------------------


def test_get_empty_symbol_list_raises(httpx_mock):
    """Test that empty symbol list raises an error."""
    with pytest.raises(ValueError, match="At least one currency symbol"):
        currency.get([], START, END)


def test_get_blank_symbol_raises():
    """Blank currency symbols fail before HTTP requests."""
    with pytest.raises(ValueError, match="non-empty"):
        currency.get("", START, END)


def test_get_invalid_date_input_raises():
    """Test that invalid date input is handled properly."""
    # Invalid date format should raise ValueError (from Date class)
    with pytest.raises(ValueError):
        currency.get("USD", "invalid-date", END)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_get_all_symbols_not_found_raises(httpx_mock):
    """Test that requesting only non-existent symbols raises error."""
    from tests.conftest import CURRENCY_ID_LIST_HTML, CURRENCY_LIST_CSV

    httpx_mock.add_response(
        url=PTAX_ID_LIST_URL,
        content=CURRENCY_ID_LIST_HTML,
        status_code=200,
    )
    httpx_mock.add_response(
        url=PTAX_CSV_DOWNLOAD_URL,
        text=CURRENCY_LIST_CSV,
        status_code=200,
    )
    # Request only non-existent currencies
    with pytest.raises(CurrencyNotFoundError):
        currency.get(["ZAR", "AUD"], START, END)


def test_get_mixed_valid_invalid_symbols(httpx_mock):
    """Test getting mix of valid and invalid symbols returns only valid ones."""
    from tests.conftest import (
        CURRENCY_ID_LIST_HTML,
        CURRENCY_LIST_CSV,
        CURRENCY_RATE_CSV,
    )

    httpx_mock.add_response(
        url=PTAX_ID_LIST_URL,
        content=CURRENCY_ID_LIST_HTML,
        status_code=200,
    )
    httpx_mock.add_response(
        url=PTAX_CSV_DOWNLOAD_URL,
        text=CURRENCY_LIST_CSV,
        status_code=200,
    )
    httpx_mock.add_response(
        url=PTAX_RATE_URL,
        text=CURRENCY_RATE_CSV,
        status_code=200,
    )
    # Request with both valid (USD) and invalid (ZAR) symbols
    # Should succeed because at least one is valid
    df = currency.get(["USD", "ZAR"], START, END)
    assert "USD" in df.columns.get_level_values(0)
    # ZAR should be skipped
    assert "ZAR" not in df.columns.get_level_values(0)


# ---------------------------------------------------------------------------
# Currency list download: roll back, retries and limits
# ---------------------------------------------------------------------------


def _csv_dates(httpx_mock):
    """Dates (YYYYMMDD) of the currency list files that were requested."""
    return [
        re.search(r"M(\d{8})\.csv", str(r.url)).group(1)
        for r in httpx_mock.get_requests()
    ]


def test_currency_list_rolls_back_to_previous_day_when_missing(httpx_mock):
    from tests.conftest import CURRENCY_LIST_CSV

    httpx_mock.add_response(url=PTAX_CSV_DOWNLOAD_URL, status_code=404)
    httpx_mock.add_response(url=PTAX_CSV_DOWNLOAD_URL, text=CURRENCY_LIST_CSV)

    res = currency._get_valid_currency_list(date.today())

    assert res.status_code == 200
    today, yesterday = date.today(), date.today() - timedelta(1)
    assert _csv_dates(httpx_mock) == [f"{today:%Y%m%d}", f"{yesterday:%Y%m%d}"]


def test_currency_list_retries_same_day_after_connection_error(httpx_mock):
    from tests.conftest import CURRENCY_LIST_CSV

    httpx_mock.add_exception(httpx.ConnectError("down"), url=PTAX_CSV_DOWNLOAD_URL)
    httpx_mock.add_response(url=PTAX_CSV_DOWNLOAD_URL, text=CURRENCY_LIST_CSV)

    res = currency._get_valid_currency_list(date.today())

    assert res.status_code == 200
    assert len(set(_csv_dates(httpx_mock))) == 1  # same date, two attempts


def test_currency_list_gives_up_after_repeated_connection_errors(httpx_mock):
    httpx_mock.add_exception(
        httpx.ConnectError("down"), url=PTAX_CSV_DOWNLOAD_URL, is_reusable=True
    )

    with pytest.raises(BCBAPIError, match="Currency list"):
        currency._get_valid_currency_list(date.today())

    assert len(httpx_mock.get_requests()) == 4  # first try + 3 retries


def test_currency_list_server_error_raises_without_rollback(httpx_mock):
    httpx_mock.add_response(url=PTAX_CSV_DOWNLOAD_URL, status_code=503)

    with pytest.raises(BCBAPIError, match="Currency list"):
        currency._get_valid_currency_list(date.today())

    assert len(httpx_mock.get_requests()) == 1


def test_currency_list_stops_after_max_rollback(httpx_mock):
    with pytest.raises(BCBAPIError, match="last 2 days") as exc:
        currency._get_valid_currency_list(date.today() - timedelta(3), max_rollback=2)

    assert exc.value.status_code == 503
    assert httpx_mock.get_requests() == []


# ---------------------------------------------------------------------------
# HTML error pages and CSV parsing
# ---------------------------------------------------------------------------


def test_extract_html_error_returns_none_for_unparseable_content():
    assert currency._extract_currency_html_error(b"") is None


def test_extract_html_error_skips_empty_error_divs():
    content = (
        b"<html><body><div class='msgErro'> - </div>"
        b"<div class='msgErro'>Moeda inexistente.</div></body></html>"
    )
    assert currency._extract_currency_html_error(content) == "Moeda inexistente"


def test_validate_csv_parser_error_raises():
    # An unclosed quote makes the CSV parser fail.
    with pytest.raises(BCBAPIError, match="Failed to parse currency CSV"):
        currency._validate_currency_csv('"01122020;220;A;USD;5,1\n')


def test_tidy_df_with_no_matching_side_returns_empty_frame():
    df = pd.DataFrame(
        {("USD", "bid"): [5.0]},
        index=pd.DatetimeIndex(["2020-12-01"], name="Date"),
    )
    df.columns = pd.MultiIndex.from_tuples(df.columns)

    tidy = currency._tidy_df(df, "ask")

    assert tidy.empty
    assert list(tidy.columns) == ["Date", "symbol", "side", "value"]


def test_cache_key_repr():
    assert repr(currency._CacheKey(type="currency_list")) == (
        "CacheKey(type='currency_list')"
    )


def test_fetch_symbol_empty_html_page_raises_api_error(httpx_mock):
    """An empty text/html response is a clear BCBAPIError, not an AttributeError."""
    from tests.conftest import CURRENCY_ID_LIST_HTML, CURRENCY_LIST_CSV

    httpx_mock.add_response(url=PTAX_ID_LIST_URL, content=CURRENCY_ID_LIST_HTML)
    httpx_mock.add_response(url=PTAX_CSV_DOWNLOAD_URL, text=CURRENCY_LIST_CSV)
    httpx_mock.add_response(
        url=PTAX_RATE_URL, content=b"", headers={"Content-Type": "text/html"}
    )

    with pytest.raises(BCBAPIError, match="USD"):
        currency.get("USD", START, END)


def test_extract_html_error_returns_none_when_parser_fails(monkeypatch):
    from lxml import etree

    def broken_parse(_):
        raise etree.ParserError("broken")

    monkeypatch.setattr(currency.html, "parse", broken_parse)
    assert currency._extract_currency_html_error(b"<html></html>") is None
