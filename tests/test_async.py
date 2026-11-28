"""Async API tests using pytest-anyio.

Tests for async_get() functions in sgs, currency, and odata modules.
"""

import re
from datetime import date, datetime, timedelta

import httpx
import pytest

from bcb import currency, sgs
from bcb.odata.api import Expectativas
from bcb.exceptions import (
    BCBAPIError,
    BCBRateLimitError,
    CurrencyNotFoundError,
    ODataError,
    SGSError,
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


async def test_async_get_tidy_multiple_codes(httpx_mock):
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

    df = await sgs.async_get([1, 11], tidy=True)

    assert list(df.columns) == ["Date", "series", "value"]
    assert set(df["series"]) == {"1", "11"}
    assert len(df) == 10


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


async def test_async_get_tidy_single_symbol(httpx_mock):
    add_currency_base_mocks(httpx_mock)
    add_currency_rate_mock(httpx_mock)

    df = await currency.async_get("USD", START, END, side="both", tidy=True)

    assert list(df.columns) == ["Date", "symbol", "side", "value"]
    assert df["symbol"].unique().tolist() == ["USD"]
    assert set(df["side"]) == {"bid", "ask"}
    assert len(df) == 10


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


async def test_async_get_tidy_enddate(httpx_mock):
    """async_get() shares the dataFim handling with get()."""
    httpx_mock.add_response(
        url=SGS_CODE_URL,
        text='[{"data":"01/01/2010","dataFim":"01/02/2010","valor":"0.0"}]',
    )
    df = await sgs.async_get({"TR": 1}, tidy=True)
    assert list(df.columns) == ["Date", "enddate", "series", "value"]


async def test_async_get_split_keeps_rows_with_same_start_date(httpx_mock):
    """async path uses the same (data, dataFim) merge key (#83)."""
    httpx_mock.add_response(
        url=SGS_CODE_URL,
        text='[{"data":"01/07/2026","dataFim":"31/07/2026","valor":"0.1711"},'
        '{"data":"01/07/2026","dataFim":"01/08/2026","valor":"0.1729"}]',
    )
    httpx_mock.add_response(
        url=SGS_CODE_URL,
        text='[{"data":"02/07/2026","dataFim":"02/08/2026","valor":"0.1750"}]',
    )
    df = await sgs.async_get({"TR": 1}, start="2016-07-01", end="2026-07-02")
    assert len(df) == 3
    assert (df.index.get_level_values("Date") == "2026-07-01").sum() == 2


def _add_expectativas_mocks(httpx_mock, response):
    base = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/"
    httpx_mock.add_response(url=base, text=ODATA_SERVICE_ROOT_JSON)
    httpx_mock.add_response(url=base + "$metadata", content=ODATA_METADATA_XML)
    httpx_mock.add_response(
        url=re.compile(r".*ExpectativasMercadoAnuais.*"), text=response
    )


async def test_async_get_keyword_arguments_and_text_output(httpx_mock):
    _add_expectativas_mocks(httpx_mock, ODATA_QUERY_RESPONSE_JSON)
    ep = Expectativas().get_endpoint("ExpectativasMercadoAnuais")

    text = await ep.async_get(filter=ep.Indicador == "IPCA", limit=1, output="text")

    assert text == ODATA_QUERY_RESPONSE_JSON
    params = httpx_mock.get_requests()[-1].url.params
    assert params["$filter"] == "Indicador eq 'IPCA'"
    assert params["$top"] == "1"


async def test_async_query_collects_dataframe(httpx_mock):
    _add_expectativas_mocks(httpx_mock, ODATA_QUERY_RESPONSE_JSON)
    ep = Expectativas().get_endpoint("ExpectativasMercadoAnuais")

    df = await ep.async_query().limit(1).async_collect()

    assert isinstance(df["Data"].iloc[0], datetime)


# ---------------------------------------------------------------------------
# Currency async error paths
# ---------------------------------------------------------------------------


async def test_async_currency_id_list_connection_error_raises(httpx_mock):
    httpx_mock.add_exception(httpx.ConnectError("down"), url=PTAX_ID_LIST_URL)

    with pytest.raises(BCBAPIError, match="Currency ID list"):
        await currency._async_currency_id_list()


async def test_async_currency_list_rolls_back_when_missing(httpx_mock):
    httpx_mock.add_response(url=PTAX_CSV_DOWNLOAD_URL, status_code=404)
    httpx_mock.add_response(url=PTAX_CSV_DOWNLOAD_URL, text=CURRENCY_LIST_CSV)

    res = await currency._async_get_valid_currency_list(date.today())

    assert res.status_code == 200
    yesterday = date.today() - timedelta(1)
    assert f"M{yesterday:%Y%m%d}.csv" in str(httpx_mock.get_requests()[-1].url)


async def test_async_currency_list_retries_then_gives_up(httpx_mock):
    httpx_mock.add_exception(
        httpx.ConnectError("down"), url=PTAX_CSV_DOWNLOAD_URL, is_reusable=True
    )

    with pytest.raises(BCBAPIError, match="Currency list"):
        await currency._async_get_valid_currency_list(date.today())

    assert len(httpx_mock.get_requests()) == 4  # first try + 3 retries


async def test_async_currency_list_server_error_raises(httpx_mock):
    httpx_mock.add_response(url=PTAX_CSV_DOWNLOAD_URL, status_code=500)

    with pytest.raises(BCBAPIError, match="Currency list"):
        await currency._async_get_valid_currency_list(date.today())


async def test_async_currency_list_stops_after_max_rollback(httpx_mock):
    with pytest.raises(BCBAPIError, match="last 2 days"):
        await currency._async_get_valid_currency_list(
            date.today() - timedelta(3), max_rollback=2
        )
    assert httpx_mock.get_requests() == []


async def test_async_currency_rate_connection_error_raises(httpx_mock):
    add_currency_base_mocks(httpx_mock)
    httpx_mock.add_exception(httpx.ConnectError("down"), url=PTAX_RATE_URL)

    with pytest.raises(BCBAPIError, match="Currency data for USD"):
        await currency.async_get("USD", START, END)


async def test_async_currency_server_error_is_raised_not_skipped(httpx_mock):
    """Only CurrencyNotFoundError is skipped; other errors reach the caller."""
    add_currency_base_mocks(httpx_mock)
    httpx_mock.add_response(url=PTAX_RATE_URL, status_code=500, is_reusable=True)

    with pytest.raises(BCBAPIError):
        await currency.async_get("USD", START, END)
    with pytest.raises(BCBAPIError):
        await currency.async_get("USD", START, END, output="text")


async def test_async_currency_text_all_unknown_raises(httpx_mock):
    add_currency_base_mocks(httpx_mock)

    with pytest.raises(CurrencyNotFoundError, match="ZAR, AUD"):
        await currency.async_get(["ZAR", "AUD"], START, END, output="text")


async def test_async_currency_text_single_symbol_returns_string(httpx_mock):
    add_currency_base_mocks(httpx_mock)
    add_currency_rate_mock(httpx_mock)

    text = await currency.async_get("USD", START, END, output="text")

    assert text == CURRENCY_RATE_CSV


# ---------------------------------------------------------------------------
# SGS async: window errors and output variants
# ---------------------------------------------------------------------------


async def test_async_get_json_connection_error_raises_sgs_error(
    httpx_mock, monkeypatch
):
    _disable_async_sgs_retry_sleep(monkeypatch)
    httpx_mock.add_exception(
        httpx.ConnectError("down"), url=SGS_CODE_URL, is_reusable=True
    )

    with pytest.raises(SGSError, match="code=1"):
        await sgs.async_get_json(1)


async def test_async_get_json_skips_empty_window(httpx_mock):
    not_found = '{"erro": {"statusCode": 404, "detail": "Value(s) not found"}}'
    httpx_mock.add_response(url=SGS_CODE_URL, status_code=404, text=not_found)
    httpx_mock.add_response(url=SGS_CODE_URL, text=SGS_JSON_5)

    text = await sgs.async_get_json(1, start="1990-01-01", end="2009-12-31")

    assert text == SGS_JSON_5


async def test_async_get_json_all_windows_empty_raises(httpx_mock):
    not_found = '{"erro": {"statusCode": 404, "detail": "Value(s) not found"}}'
    httpx_mock.add_response(
        url=SGS_CODE_URL, status_code=404, text=not_found, is_reusable=True
    )

    with pytest.raises(SGSError, match="not found"):
        await sgs.async_get_json(1, start="1990-01-01", end="2009-12-31")


async def test_async_get_text_multiple_codes_returns_dict(httpx_mock):
    httpx_mock.add_response(url=SGS_CODE_URL, text=SGS_JSON_5, is_reusable=True)

    result = await sgs.async_get([1, 2], last=5, output="text")

    assert result == {1: SGS_JSON_5, 2: SGS_JSON_5}


async def test_async_get_multi_false_returns_list(httpx_mock):
    httpx_mock.add_response(url=SGS_CODE_URL, text=SGS_JSON_5, is_reusable=True)

    result = await sgs.async_get({"A": 1, "B": 2}, last=5, multi=False)

    assert [list(df.columns) for df in result] == [["A"], ["B"]]


async def test_async_odata_get_verbose_prints_query(httpx_mock, capsys):
    _add_expectativas_mocks(httpx_mock, ODATA_QUERY_RESPONSE_JSON)
    ep = Expectativas().get_endpoint("ExpectativasMercadoAnuais")

    await ep.async_get(limit=1, verbose=True)

    assert "ExpectativasMercadoAnuais" in capsys.readouterr().out
