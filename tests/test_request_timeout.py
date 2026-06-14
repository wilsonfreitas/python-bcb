from datetime import datetime
from typing import Any

import httpx
import pandas as pd
import pytest

from bcb import currency, sgs
from bcb import http as http_module
from bcb.odata import framework as odata_framework
from bcb.odata.api import Expectativas
from tests.conftest import (
    CURRENCY_ID_LIST_HTML,
    CURRENCY_LIST_CSV,
    CURRENCY_RATE_CSV,
    ODATA_METADATA_XML,
    ODATA_QUERY_RESPONSE_JSON,
    ODATA_SERVICE_ROOT_JSON,
    SGS_JSON_5,
)

START = datetime(2020, 12, 1)
END = datetime(2020, 12, 7)
EXPECTATIVAS_BASE_URL = (
    "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/"
)


class RecordingClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        self.calls.append((url, kwargs.copy()))
        return response_for_url(url)


class AsyncRecordingClient(RecordingClient):
    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        self.calls.append((url, kwargs.copy()))
        return response_for_url(url)


def response_for_url(url: str) -> httpx.Response:
    request = httpx.Request("GET", url)
    if "bcdata.sgs" in url:
        return httpx.Response(200, text=SGS_JSON_5, request=request)
    if "exibeFormularioConsultaBoletim" in url:
        return httpx.Response(200, content=CURRENCY_ID_LIST_HTML, request=request)
    if "Download/fechamento" in url:
        return httpx.Response(200, text=CURRENCY_LIST_CSV, request=request)
    if "gerarCSVFechamento" in url:
        return httpx.Response(
            200,
            text=CURRENCY_RATE_CSV,
            headers={"Content-Type": "text/csv"},
            request=request,
        )
    if url == EXPECTATIVAS_BASE_URL:
        return httpx.Response(200, text=ODATA_SERVICE_ROOT_JSON, request=request)
    if url.endswith("$" + "metadata"):
        return httpx.Response(200, content=ODATA_METADATA_XML, request=request)
    if "ExpectativasMercadoAnuais" in url:
        return httpx.Response(200, text=ODATA_QUERY_RESPONSE_JSON, request=request)
    raise AssertionError(f"unexpected URL: {url}")


def timeout_values(client: RecordingClient) -> list[Any]:
    return [kwargs.get("timeout") for _, kwargs in client.calls]


def test_timeout_kwargs_omits_none_to_keep_client_default() -> None:
    assert http_module.timeout_kwargs(None) == {}
    assert http_module.timeout_kwargs(45.0) == {"timeout": 45.0}


def test_sgs_get_passes_timeout_to_request(monkeypatch: pytest.MonkeyPatch) -> None:
    client = RecordingClient()
    monkeypatch.setattr(sgs, "get_client", lambda: client)

    df = sgs.get(1, timeout=45.0)

    assert isinstance(df, pd.DataFrame)
    assert timeout_values(client) == [45.0]


def test_sgs_get_uses_client_default_when_timeout_omitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = RecordingClient()
    monkeypatch.setattr(sgs, "get_client", lambda: client)

    sgs.get_json(1)

    assert "timeout" not in client.calls[0][1]


def test_currency_get_passes_timeout_to_all_initial_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = RecordingClient()
    monkeypatch.setattr(currency, "get_client", lambda: client)

    df = currency.get("USD", START, END, timeout=60.0)

    assert isinstance(df, pd.DataFrame)
    assert len(client.calls) == 3
    assert timeout_values(client) == [60.0, 60.0, 60.0]


def test_currency_get_currency_list_passes_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = RecordingClient()
    monkeypatch.setattr(currency, "get_client", lambda: client)

    df = currency.get_currency_list(timeout=15.0)

    assert isinstance(df, pd.DataFrame)
    assert timeout_values(client) == [15.0]


def test_odata_api_and_endpoint_pass_timeouts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = RecordingClient()
    monkeypatch.setattr(odata_framework, "get_client", lambda: client)

    api = Expectativas(timeout=12.0)
    endpoint = api.get_endpoint("ExpectativasMercadoAnuais")
    data = endpoint.get(timeout=24.0)

    assert isinstance(data, pd.DataFrame)
    assert timeout_values(client) == [12.0, 12.0, 24.0]


def test_odata_query_uses_api_timeout_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = RecordingClient()
    monkeypatch.setattr(odata_framework, "get_client", lambda: client)

    api = Expectativas(timeout=18.0)
    endpoint = api.get_endpoint("ExpectativasMercadoAnuais")
    endpoint.query().limit(1).text()

    assert timeout_values(client) == [18.0, 18.0, 18.0]


@pytest.mark.anyio
async def test_async_sgs_get_json_passes_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = AsyncRecordingClient()
    monkeypatch.setattr(sgs, "get_async_client", lambda: client)

    result = await sgs.async_get_json(1, timeout=30.0)

    assert result == SGS_JSON_5
    assert timeout_values(client) == [30.0]


@pytest.mark.anyio
async def test_async_currency_get_passes_timeout_to_all_initial_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = AsyncRecordingClient()
    monkeypatch.setattr(currency, "get_async_client", lambda: client)

    df = await currency.async_get("USD", START, END, timeout=35.0)

    assert isinstance(df, pd.DataFrame)
    assert len(client.calls) == 3
    assert timeout_values(client) == [35.0, 35.0, 35.0]


@pytest.mark.anyio
async def test_async_odata_endpoint_passes_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sync_client = RecordingClient()
    async_client = AsyncRecordingClient()
    monkeypatch.setattr(odata_framework, "get_client", lambda: sync_client)
    monkeypatch.setattr(odata_framework, "get_async_client", lambda: async_client)

    api = Expectativas(timeout=14.0)
    endpoint = api.get_endpoint("ExpectativasMercadoAnuais")
    data = await endpoint.async_get(timeout=28.0)

    assert isinstance(data, pd.DataFrame)
    assert timeout_values(sync_client) == [14.0, 14.0]
    assert timeout_values(async_client) == [28.0]
