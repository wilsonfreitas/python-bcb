import re
from datetime import datetime

import pandas as pd
import pytest

from bcb.odata.api import Expectativas
from bcb.odata.framework import ODataPropertyFilter, ODataPropertyOrderBy
from bcb.exceptions import ODataError
from tests.conftest import (
    ODATA_SERVICE_ROOT_JSON,
    ODATA_METADATA_XML,
    ODATA_QUERY_RESPONSE_JSON,
)

EXPECTATIVAS_BASE_URL = (
    "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/"
)
EXPECTATIVAS_METADATA_URL = (
    "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/$metadata"
)
ENTITY_URL_PATTERN = re.compile(r".*ExpectativasMercadoAnuais.*")


def add_service_mocks(httpx_mock):
    """Add the two requests needed to instantiate any BaseODataAPI subclass."""
    httpx_mock.add_response(
        url=EXPECTATIVAS_BASE_URL,
        text=ODATA_SERVICE_ROOT_JSON,
        status_code=200,
    )
    httpx_mock.add_response(
        url=EXPECTATIVAS_METADATA_URL,
        content=ODATA_METADATA_XML,
        status_code=200,
    )


# ---------------------------------------------------------------------------
# Service / metadata instantiation
# ---------------------------------------------------------------------------


def test_service_discovers_entity_sets(httpx_mock):
    add_service_mocks(httpx_mock)
    api = Expectativas()
    assert "ExpectativasMercadoAnuais" in api.service.entity_sets


def test_endpoint_exposes_properties(httpx_mock):
    add_service_mocks(httpx_mock)
    api = Expectativas()
    ep = api.get_endpoint("ExpectativasMercadoAnuais")
    assert hasattr(ep, "Indicador")
    assert hasattr(ep, "Data")
    assert hasattr(ep, "Mediana")


def test_invalid_endpoint_raises(httpx_mock):
    add_service_mocks(httpx_mock)
    api = Expectativas()
    with pytest.raises(ODataError, match="Invalid name"):
        api.get_endpoint("DoesNotExist")


# ---------------------------------------------------------------------------
# ODataProperty operator overloading
# ---------------------------------------------------------------------------


def test_string_property_equality_filter(httpx_mock):
    add_service_mocks(httpx_mock)
    api = Expectativas()
    ep = api.get_endpoint("ExpectativasMercadoAnuais")
    f = ep.Indicador == "IPCA"
    assert isinstance(f, ODataPropertyFilter)
    assert str(f) == "Indicador eq 'IPCA'"


def test_decimal_property_comparison_filters(httpx_mock):
    add_service_mocks(httpx_mock)
    api = Expectativas()
    ep = api.get_endpoint("ExpectativasMercadoAnuais")
    mediana = ep.Mediana
    assert str(mediana > 4.0) == "Mediana gt 4.0"
    assert str(mediana >= 4.0) == "Mediana ge 4.0"
    assert str(mediana < 4.0) == "Mediana lt 4.0"
    assert str(mediana <= 4.0) == "Mediana le 4.0"


def test_property_orderby(httpx_mock):
    add_service_mocks(httpx_mock)
    api = Expectativas()
    ep = api.get_endpoint("ExpectativasMercadoAnuais")
    assert isinstance(ep.Mediana.asc(), ODataPropertyOrderBy)
    assert str(ep.Mediana.asc()) == "Mediana asc"
    assert str(ep.Mediana.desc()) == "Mediana desc"


# ---------------------------------------------------------------------------
# Query chain building
# ---------------------------------------------------------------------------


def test_query_limit(httpx_mock):
    add_service_mocks(httpx_mock)
    httpx_mock.add_response(
        url=ENTITY_URL_PATTERN,
        text=ODATA_QUERY_RESPONSE_JSON,
        status_code=200,
    )
    api = Expectativas()
    ep = api.get_endpoint("ExpectativasMercadoAnuais")
    df = ep.query().limit(1).collect()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert list(df.columns) == ["Indicador", "Data", "Mediana"]


def test_query_date_column_converted(httpx_mock):
    add_service_mocks(httpx_mock)
    httpx_mock.add_response(
        url=ENTITY_URL_PATTERN,
        text=ODATA_QUERY_RESPONSE_JSON,
        status_code=200,
    )
    api = Expectativas()
    ep = api.get_endpoint("ExpectativasMercadoAnuais")
    df = ep.query().limit(1).collect()
    assert isinstance(df["Data"].iloc[0], datetime)


def test_endpoint_get_shortcut(httpx_mock):
    add_service_mocks(httpx_mock)
    httpx_mock.add_response(
        url=ENTITY_URL_PATTERN,
        text=ODATA_QUERY_RESPONSE_JSON,
        status_code=200,
    )
    api = Expectativas()
    ep = api.get_endpoint("ExpectativasMercadoAnuais")
    df = ep.get(limit=1)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
