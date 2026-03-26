"""Async API tests using pytest-anyio.

Tests for async_get() functions in sgs, currency, and odata modules.
"""

import re
from datetime import datetime

import pytest

from bcb import currency, sgs
from bcb.odata.api import Expectativas
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


# ---------------------------------------------------------------------------
# Currency async tests
# ---------------------------------------------------------------------------


async def test_async_get_symbol_returns_dataframe(httpx_mock):
    """Test async_get_symbol() returns DataFrame."""
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
        headers={"Content-Type": "text/csv"},
    )
    df = await currency._async_get_symbol("USD", START, END)
    assert df is not None
    assert ("USD", "bid") in df.columns
    assert ("USD", "ask") in df.columns


async def test_async_get_single_symbol_returns_dataframe(httpx_mock):
    """Test async_get() with single symbol returns DataFrame."""
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
        headers={"Content-Type": "text/csv"},
    )
    df = await currency.async_get("USD", START, END)
    assert df is not None


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
