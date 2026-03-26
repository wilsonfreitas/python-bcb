"""Negative test cases for bcb.currency module.

Tests for error handling, malformed data, and edge cases.
"""

import re
from datetime import datetime

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
    with pytest.raises(BCBAPIError):
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
    with pytest.raises(BCBAPIError):
        currency._get_symbol("USD", START, END)


# ---------------------------------------------------------------------------
# Invalid input handling
# ---------------------------------------------------------------------------


def test_get_empty_symbol_list_raises(httpx_mock):
    """Test that empty symbol list raises an error."""
    with pytest.raises((ValueError, CurrencyNotFoundError)):
        currency.get([], START, END)


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
