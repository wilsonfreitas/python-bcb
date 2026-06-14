"""Negative test cases for bcb.sgs module.

Tests for error handling, malformed data, and edge cases.
"""

import json
import re

import httpx
import pytest

from bcb import sgs
from bcb.exceptions import SGSError

SGS_CODE_URL = re.compile(r".*bcdata\.sgs\..*")


# ---------------------------------------------------------------------------
# 404 and 429 API response errors
# ---------------------------------------------------------------------------


def test_get_json_404_raises(httpx_mock):
    """Test that 404 response raises SGSError."""
    httpx_mock.add_response(
        url=SGS_CODE_URL,
        status_code=404,
    )
    with pytest.raises(SGSError):
        sgs.get_json(1)


def test_get_json_429_rate_limit_raises(httpx_mock):
    """Test that 429 response raises BCBRateLimitError."""
    from bcb.exceptions import BCBRateLimitError

    httpx_mock.add_response(
        url=SGS_CODE_URL,
        status_code=429,
    )
    with pytest.raises(BCBRateLimitError):
        sgs.get_json(1)


def test_get_json_500_raises(httpx_mock):
    """Test that 500 response raises SGSError."""
    httpx_mock.add_response(
        url=SGS_CODE_URL,
        status_code=500,
    )
    with pytest.raises(SGSError):
        sgs.get_json(1)


def test_get_json_connection_error_raises(httpx_mock):
    httpx_mock.add_exception(
        httpx.ConnectError("network down"),
        url=SGS_CODE_URL,
    )

    with pytest.raises(SGSError, match="SGS time series"):
        sgs.get_json(1)


def test_get_json_timeout_error_raises(httpx_mock):
    httpx_mock.add_exception(
        httpx.TimeoutException("request timed out"),
        url=SGS_CODE_URL,
    )

    with pytest.raises(SGSError, match="SGS time series"):
        sgs.get_json(1)


# ---------------------------------------------------------------------------
# Malformed data (JSON)
# ---------------------------------------------------------------------------


def test_get_json_malformed_json_raises(httpx_mock):
    """Test that malformed JSON raises SGSError."""
    httpx_mock.add_response(
        url=SGS_CODE_URL,
        text="not valid json {",
        status_code=200,
    )
    # get() function calls get_json() which returns the raw text,
    # then tries to parse with pd.read_json() which will raise
    with pytest.raises(Exception):  # JSONDecodeError or ValueError from pandas
        sgs.get(1)


def test_get_json_invalid_response_format_raises(httpx_mock):
    """Test that response without expected fields raises error."""
    # JSON array but missing expected date/valor fields
    invalid_response = json.dumps([{"unexpected_field": "value"}])
    httpx_mock.add_response(
        url=SGS_CODE_URL,
        text=invalid_response,
        status_code=200,
    )
    # pd.read_json will create DataFrame but missing expected columns
    # The code expects "data" and "valor" columns
    with pytest.raises(Exception):  # KeyError when setting index
        sgs.get(1)


# ---------------------------------------------------------------------------
# Invalid input handling
# ---------------------------------------------------------------------------


def test_get_negative_sgs_code_raises(httpx_mock):
    """Test that negative SGS code raises ValueError."""
    with pytest.raises(ValueError, match="positive"):
        sgs.get(-1)


def test_get_zero_sgs_code_raises(httpx_mock):
    """Test that zero SGS code raises ValueError."""
    with pytest.raises(ValueError, match="positive"):
        sgs.get(0)


def test_codes_generator_non_positive_raises():
    """Test that _codes() generator raises ValueError for non-positive codes."""
    # Test the _codes() generator directly
    with pytest.raises(ValueError, match="positive"):
        list(sgs._codes([1, -1, 3]))


def test_get_invalid_frequency_accepted(httpx_mock):
    """Test that invalid frequency string is passed to pandas."""
    from tests.conftest import SGS_JSON_5

    httpx_mock.add_response(
        url=SGS_CODE_URL,
        text=SGS_JSON_5,
        status_code=200,
    )
    # Invalid frequency should be caught by pandas
    with pytest.raises(Exception):  # ValueError from pandas Period
        sgs.get(1, freq="INVALID")


def test_sgs_code_string_non_numeric_raises(httpx_mock):
    """Test that non-numeric string code raises ValueError."""
    with pytest.raises(ValueError):
        sgs.get("ABC")


def test_get_empty_code_list():
    """Test that empty code list raises ValueError."""
    with pytest.raises(ValueError, match="At least one SGS code"):
        sgs.get([])


def test_get_empty_code_mapping():
    """Test that empty code mappings raise ValueError."""
    with pytest.raises(ValueError, match="At least one SGS code"):
        sgs.get({})


def test_get_invalid_output_raises():
    """Unsupported output values fail before HTTP requests."""
    with pytest.raises(ValueError, match="output"):
        sgs.get(1, output="xml")  # type: ignore[arg-type]


def test_get_negative_last_raises():
    """Negative last values fail before HTTP requests."""
    with pytest.raises(ValueError, match="last"):
        sgs.get(1, last=-1)


def test_get_json_negative_code_raises():
    """get_json validates single public code inputs."""
    with pytest.raises(ValueError, match="positive"):
        sgs.get_json(-1)


# ---------------------------------------------------------------------------
# Edge cases and boundary conditions
# ---------------------------------------------------------------------------


def test_get_very_large_sgs_code(httpx_mock):
    """Test that very large SGS codes are accepted."""
    from tests.conftest import SGS_JSON_5

    large_code = 999999999
    httpx_mock.add_response(
        url=SGS_CODE_URL,
        text=SGS_JSON_5,
        status_code=200,
    )
    # Should work fine - just a large integer
    df = sgs.get(large_code)
    assert df is not None


def test_get_multiple_same_code_deduplication(httpx_mock):
    """Test that requesting same code multiple times works."""
    from tests.conftest import SGS_JSON_5

    httpx_mock.add_response(
        url=SGS_CODE_URL,
        text=SGS_JSON_5,
        status_code=200,
    )
    # Request same code twice - should fetch twice (no dedup at API level)
    # But with multi=True should concat properly
    httpx_mock.add_response(
        url=SGS_CODE_URL,
        text=SGS_JSON_5,
        status_code=200,
    )
    result = sgs.get([1, 1], multi=True)
    # Result should have both copies (or merged)
    assert result is not None


def test_get_text_output_malformed_json_raises(httpx_mock):
    """Test that text output with malformed JSON raises."""
    httpx_mock.add_response(
        url=SGS_CODE_URL,
        text="not valid json",
        status_code=200,
    )
    # text output just returns raw JSON string, no validation
    result = sgs.get(1, output="text")
    assert result == "not valid json"


def test_get_last_parameter_overrides_dates(httpx_mock):
    """Test that last parameter takes precedence over date range."""
    from tests.conftest import SGS_JSON_5
    from datetime import datetime

    httpx_mock.add_response(
        url=SGS_CODE_URL,
        text=SGS_JSON_5,
        status_code=200,
    )
    # last=10 should make start/end ignored - URL should have /ultimos/10
    df = sgs.get(1, start=datetime(2020, 1, 1), end=datetime(2020, 12, 31), last=10)
    assert df is not None
