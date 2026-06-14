"""Async API tests using pytest-anyio.

Tests for async_get() functions in sgs, currency, and odata modules.
"""

import re
from datetime import datetime

import httpx
import pytest

from bcb import currency, sgs
from bcb.odata.api import Expectativas
from bcb.exceptions import (
    BCBAPIError,
    BCBRateLimitError,
    CurrencyNotFoundError,
    ODataError,
)
from tests.conftest import (
    CURRENCY_ID_LIST_HTML,
    CURRENCY_LIST_CSV,
    CURRENCY_RATE_CSV,
    SGS_JSON_5,
    ODATA_METADATA_XML,
    ODATA_SERVICE_ROOT_JSON,
    ODATA_QUERY_RESPONSE_JSON,
)

pytestmark = pytest.mark.anyio

START = datetime(2020, 12, 1)
END = datetime(2020, 12, 7)

PTAX_ID_LIST_URL = re.compile(r".*exibeFormularioConsultaBoletim.*")
PTAX_CSV_DOWNLOAD_URL = re.compile(r".*www4\.bcb\.gov\.br.*\.csv")
PTAX_RATE_URL = re.compile(r".*gerarCSVFechamento.*")
SGS_CODE_URL = re.compile(r".*bcdata\.sgs\..*")


async def _async_no_retry_sleep(_):
    return None


def _disable_async_sgs_retry_sleep(monkeypatch):
    monkeypatch.setattr(
        sgs._async_get_sgs_response.retry, "sleep", _async_no_retry_sleep
    )


def add_currency_base_mocks(httpx_mock):
    httpx_mock.add_response(
        url=PTAX_ID_LIST_URL,
        content=CURRENCY_ID_LIST_HTML,
        status_code=200,
        is_reusable=True,
    )
    httpx_mock.add_response(
        url=PTAX_CSV_DOWNLOAD_URL,
        text=CURRENCY_LIST_CSV,
        status_code=200,
        is_reusable=True,
    )


def add_currency_rate_mock(httpx_mock):
    httpx_mock.add_response(
        url=PTAX_RATE_URL,
        text=CURRENCY_RATE_CSV,
        status_code=200,
        headers={"Content-Type": "text/csv"},
        is_reusable=True,
    )


# ---------------------------------------------------------------------------
# SGS async tests
# ---------------------------------------------------------------------------


async def test_async_get_json_single_code(httpx_mock):
    """Test async_get_json() with a single code."""
    httpx_mock.add_response(
        url=SGS_CODE_URL,
        text=SGS_JSON_5,
        status_code=200,
    )
    result = await sgs.async_get_json(1)
    assert isinstance(result, str)
    assert "data" in result
    assert "valor" in result


async def test_async_get_single_code_returns_dataframe(httpx_mock):
    """Test async_get() with a single code returns DataFrame."""
    httpx_mock.add_response(
        url=SGS_CODE_URL,
        text=SGS_JSON_5,
        status_code=200,
    )
    df = await sgs.async_get(1)
    assert df is not None
    assert len(df) == 5


async def test_async_get_multiple_codes_concurrent(httpx_mock):
    """Test async_get() with multiple codes uses concurrent requests."""
    # Add response for each code - should be called concurrently
    httpx_mock.add_response(
        url=SGS_CODE_URL,
        text=SGS_JSON_5,
        status_code=200,
    )
    httpx_mock.add_response(
        url=SGS_CODE_URL,
        text=SGS_JSON_5,
        status_code=200,
    )
    df = await sgs.async_get([1, 11], multi=True)
    assert df is not None
    # Should have two columns (one for each code)
    assert df.shape[1] == 2


async def test_async_get_text_output(httpx_mock):
    """Test async_get() with output='text' returns JSON string."""
    httpx_mock.add_response(
        url=SGS_CODE_URL,
        text=SGS_JSON_5,
        status_code=200,
    )
    result = await sgs.async_get(1, output="text")
    assert isinstance(result, str)
    assert "data" in result


async def test_async_get_json_rate_limit_raises(httpx_mock):
    httpx_mock.add_response(
        url=SGS_CODE_URL,
        status_code=429,
    )

    with pytest.raises(BCBRateLimitError):
        await sgs.async_get_json(1)


async def test_async_get_json_retries_timeout_then_succeeds(httpx_mock, monkeypatch):
    _disable_async_sgs_retry_sleep(monkeypatch)
    httpx_mock.add_exception(
        httpx.TimeoutException("request timed out"),
        url=SGS_CODE_URL,
    )
    httpx_mock.add_response(
        url=SGS_CODE_URL,
        text=SGS_JSON_5,
        status_code=200,
    )

    result = await sgs.async_get_json(1)

    assert result == SGS_JSON_5


async def test_async_get_empty_sgs_code_list_raises():
    with pytest.raises(ValueError, match="At least one SGS code"):
        await sgs.async_get([])


async def test_async_get_invalid_sgs_output_raises():
    with pytest.raises(ValueError, match="output"):
        await sgs.async_get(1, output="xml")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Currency async tests
# ---------------------------------------------------------------------------


async def test_async_get_symbol_returns_dataframe(httpx_mock):
    """Test async_get_symbol() returns DataFrame."""
    add_currency_base_mocks(httpx_mock)
    add_currency_rate_mock(httpx_mock)
    df = await currency._async_get_symbol("USD", START, END)
    assert df is not None
    assert ("USD", "bid") in df.columns
    assert ("USD", "ask") in df.columns


async def test_async_get_single_symbol_returns_dataframe(httpx_mock):
    """Test async_get() with single symbol returns DataFrame."""
    add_currency_base_mocks(httpx_mock)
    add_currency_rate_mock(httpx_mock)
    df = await currency.async_get("USD", START, END)
    assert df is not None


async def test_async_get_invalid_currency_side_raises():
    with pytest.raises(ValueError, match="Unknown side"):
        await currency.async_get("USD", START, END, side="mid")  # type: ignore[arg-type]


async def test_async_get_invalid_currency_output_raises():
    with pytest.raises(ValueError, match="Unknown output"):
        await currency.async_get("USD", START, END, output="json")  # type: ignore[arg-type]


async def test_async_get_mixed_valid_invalid_symbols_returns_valid_dataframe(
    httpx_mock,
):
    add_currency_base_mocks(httpx_mock)
    add_currency_rate_mock(httpx_mock)

    df = await currency.async_get(["USD", "ZAR"], START, END, side="both")

    assert "USD" in df.columns.get_level_values(0)
    assert "ZAR" not in df.columns.get_level_values(0)


async def test_async_get_duplicate_symbols_returns_duplicate_columns(httpx_mock):
    add_currency_base_mocks(httpx_mock)
    add_currency_rate_mock(httpx_mock)

    df = await currency.async_get(["USD", "USD"], START, END, side="both")

    assert list(df.columns.get_level_values(0)).count("USD") == 4


async def test_async_get_mixed_valid_invalid_text_returns_valid_dict(httpx_mock):
    add_currency_base_mocks(httpx_mock)
    add_currency_rate_mock(httpx_mock)

    result = await currency.async_get(["USD", "ZAR"], START, END, output="text")

    assert isinstance(result, dict)
    assert list(result) == ["USD"]
    assert "01122020" in result["USD"]


async def test_async_get_all_invalid_symbols_raise_clear_error(httpx_mock):
    add_currency_base_mocks(httpx_mock)

    with pytest.raises(
        CurrencyNotFoundError,
        match="No valid currency symbols found: ZAR, ZZ1",
    ):
        await currency.async_get(["ZAR", "ZZ1"], START, END)


async def test_async_get_all_invalid_text_symbols_raise_clear_error(httpx_mock):
    add_currency_base_mocks(httpx_mock)

    with pytest.raises(
        CurrencyNotFoundError,
        match="No valid currency symbols found: ZAR, ZZ1",
    ):
        await currency.async_get(["ZAR", "ZZ1"], START, END, output="text")


async def test_async_get_symbol_unexpected_html_raises_bcb_error(httpx_mock):
    add_currency_base_mocks(httpx_mock)
    httpx_mock.add_response(
        url=PTAX_RATE_URL,
        text="<html><body><p>temporary failure</p></body></html>",
        status_code=200,
        headers={},
    )

    with pytest.raises(BCBAPIError, match="HTML response.*USD.*recognized"):
        await currency._async_get_symbol("USD", START, END)


async def test_async_get_symbol_empty_response_body_raises_bcb_error(httpx_mock):
    add_currency_base_mocks(httpx_mock)
    httpx_mock.add_response(
        url=PTAX_RATE_URL,
        text="",
        status_code=200,
        headers={"Content-Type": "text/csv"},
    )

    with pytest.raises(BCBAPIError, match="empty"):
        await currency._async_get_symbol("USD", START, END)


# ---------------------------------------------------------------------------
# OData async tests
# ---------------------------------------------------------------------------


async def test_odata_query_async_text(httpx_mock):
    """Test ODataQuery.async_text() returns JSON string."""
    httpx_mock.add_response(
        url="https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/",
        text=ODATA_SERVICE_ROOT_JSON,
        status_code=200,
    )
    httpx_mock.add_response(
        url="https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/$metadata",
        content=ODATA_METADATA_XML,
        status_code=200,
    )
    httpx_mock.add_response(
        url=re.compile(r".*ExpectativasMercadoAnuais.*"),
        text=ODATA_QUERY_RESPONSE_JSON,
        status_code=200,
    )
    api = Expectativas()
    ep = api.get_endpoint("ExpectativasMercadoAnuais")
    result = await ep.query().limit(1).async_text()
    assert isinstance(result, str)
    assert "value" in result


async def test_odata_query_async_status_error_raises(httpx_mock):
    httpx_mock.add_response(
        url="https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/",
        text=ODATA_SERVICE_ROOT_JSON,
        status_code=200,
    )
    httpx_mock.add_response(
        url="https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/$metadata",
        content=ODATA_METADATA_XML,
        status_code=200,
    )
    httpx_mock.add_response(
        url=re.compile(r".*ExpectativasMercadoAnuais.*"),
        text="server error",
        status_code=500,
    )

    api = Expectativas()
    ep = api.get_endpoint("ExpectativasMercadoAnuais")

    with pytest.raises(ODataError, match="OData query"):
        await ep.query().limit(1).async_text()


async def test_odata_query_async_transport_error_raises(httpx_mock):
    httpx_mock.add_response(
        url="https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/",
        text=ODATA_SERVICE_ROOT_JSON,
        status_code=200,
    )
    httpx_mock.add_response(
        url="https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/$metadata",
        content=ODATA_METADATA_XML,
        status_code=200,
    )
    httpx_mock.add_exception(
        httpx.ConnectError("network down"),
        url=re.compile(r".*ExpectativasMercadoAnuais.*"),
    )

    api = Expectativas()
    ep = api.get_endpoint("ExpectativasMercadoAnuais")

    with pytest.raises(ODataError, match="OData query.*network down"):
        await ep.query().limit(1).async_text()


async def test_odata_query_async_malformed_json_raises(httpx_mock):
    httpx_mock.add_response(
        url="https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/",
        text=ODATA_SERVICE_ROOT_JSON,
        status_code=200,
    )
    httpx_mock.add_response(
        url="https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/$metadata",
        content=ODATA_METADATA_XML,
        status_code=200,
    )
    httpx_mock.add_response(
        url=re.compile(r".*ExpectativasMercadoAnuais.*"),
        text="not json",
        status_code=200,
    )

    api = Expectativas()
    ep = api.get_endpoint("ExpectativasMercadoAnuais")

    with pytest.raises(ODataError, match="OData query.*invalid JSON"):
        await ep.query().limit(1).async_collect()


async def test_odata_query_async_collect(httpx_mock):
    """Test ODataQuery.async_collect() returns DataFrame."""
    httpx_mock.add_response(
        url="https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/",
        text=ODATA_SERVICE_ROOT_JSON,
        status_code=200,
    )
    httpx_mock.add_response(
        url="https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/$metadata",
        content=ODATA_METADATA_XML,
        status_code=200,
    )
    httpx_mock.add_response(
        url=re.compile(r".*ExpectativasMercadoAnuais.*"),
        text=ODATA_QUERY_RESPONSE_JSON,
        status_code=200,
    )
    api = Expectativas()
    ep = api.get_endpoint("ExpectativasMercadoAnuais")
    df = await ep.query().limit(1).async_collect()
    assert df is not None
    assert len(df) == 1


async def test_endpoint_async_get(httpx_mock):
    """Test Endpoint.async_get() shortcut."""
    httpx_mock.add_response(
        url="https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/",
        text=ODATA_SERVICE_ROOT_JSON,
        status_code=200,
    )
    httpx_mock.add_response(
        url="https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/$metadata",
        content=ODATA_METADATA_XML,
        status_code=200,
    )
    httpx_mock.add_response(
        url=re.compile(r".*ExpectativasMercadoAnuais.*"),
        text=ODATA_QUERY_RESPONSE_JSON,
        status_code=200,
    )
    api = Expectativas()
    ep = api.get_endpoint("ExpectativasMercadoAnuais")
    df = await ep.async_get(limit=1)
    assert df is not None
    assert len(df) == 1
