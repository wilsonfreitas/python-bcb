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
    ODATA_QUERY_RESPONSE_MULTI_DATE_JSON,
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


# ---------------------------------------------------------------------------
# DATE_COLUMNS — configurable date detection (Phase 7.1)
# ---------------------------------------------------------------------------


class _SingleDateAPI(Expectativas):
    """API subclass that restricts date conversion to 'Data' only."""

    DATE_COLUMNS = ["Data"]


class _AltDateAPI(Expectativas):
    """API subclass that restricts date conversion to 'DataVigencia' only."""

    DATE_COLUMNS = ["DataVigencia"]


def test_date_columns_default_empty_uses_heuristic(httpx_mock):
    """When DATE_COLUMNS is empty (default), the built-in heuristic fires."""
    add_service_mocks(httpx_mock)
    httpx_mock.add_response(
        url=ENTITY_URL_PATTERN,
        text=ODATA_QUERY_RESPONSE_MULTI_DATE_JSON,
        status_code=200,
    )
    api = Expectativas()  # DATE_COLUMNS = []
    ep = api.get_endpoint("ExpectativasMercadoAnuais")
    df = ep.query().limit(1).collect()
    # Heuristic converts both "Data" and "DataVigencia"
    assert isinstance(df["Data"].iloc[0], datetime)
    assert isinstance(df["DataVigencia"].iloc[0], datetime)


def test_date_columns_explicit_list_converts_only_listed(httpx_mock):
    """When DATE_COLUMNS lists only 'Data', only that column is converted."""
    add_service_mocks(httpx_mock)
    httpx_mock.add_response(
        url=ENTITY_URL_PATTERN,
        text=ODATA_QUERY_RESPONSE_MULTI_DATE_JSON,
        status_code=200,
    )
    api = _SingleDateAPI()
    ep = api.get_endpoint("ExpectativasMercadoAnuais")
    df = ep.query().limit(1).collect()
    assert isinstance(df["Data"].iloc[0], datetime)
    # DataVigencia is NOT in DATE_COLUMNS so it stays as a raw string
    assert isinstance(df["DataVigencia"].iloc[0], str)


def test_date_columns_explicit_list_alternate_column(httpx_mock):
    """When DATE_COLUMNS lists only 'DataVigencia', only that column is converted."""
    add_service_mocks(httpx_mock)
    httpx_mock.add_response(
        url=ENTITY_URL_PATTERN,
        text=ODATA_QUERY_RESPONSE_MULTI_DATE_JSON,
        status_code=200,
    )
    api = _AltDateAPI()
    ep = api.get_endpoint("ExpectativasMercadoAnuais")
    df = ep.query().limit(1).collect()
    assert isinstance(df["DataVigencia"].iloc[0], datetime)
    # Data is NOT in DATE_COLUMNS so it stays as a raw string
    assert isinstance(df["Data"].iloc[0], str)


def test_date_columns_propagates_through_get_shortcut(httpx_mock):
    """DATE_COLUMNS applies to ep.get() as well as ep.query().collect()."""
    add_service_mocks(httpx_mock)
    httpx_mock.add_response(
        url=ENTITY_URL_PATTERN,
        text=ODATA_QUERY_RESPONSE_MULTI_DATE_JSON,
        status_code=200,
    )
    api = _SingleDateAPI()
    ep = api.get_endpoint("ExpectativasMercadoAnuais")
    df = ep.get(limit=1)
    assert isinstance(df["Data"].iloc[0], datetime)
    assert isinstance(df["DataVigencia"].iloc[0], str)


# ---------------------------------------------------------------------------
# output="text" — raw OData JSON response
# ---------------------------------------------------------------------------


def test_collect_output_text_returns_string(httpx_mock):
    """collect(output='text') returns the raw JSON string from the API."""
    add_service_mocks(httpx_mock)
    httpx_mock.add_response(
        url=ENTITY_URL_PATTERN,
        text=ODATA_QUERY_RESPONSE_JSON,
        status_code=200,
    )
    api = Expectativas()
    ep = api.get_endpoint("ExpectativasMercadoAnuais")
    result = ep.query().limit(1).collect(output="text")
    assert isinstance(result, str)
    assert '"value"' in result
    assert "IPCA" in result


def test_endpoint_get_output_text_returns_string(httpx_mock):
    """ep.get(output='text') returns the raw JSON string from the API."""
    add_service_mocks(httpx_mock)
    httpx_mock.add_response(
        url=ENTITY_URL_PATTERN,
        text=ODATA_QUERY_RESPONSE_JSON,
        status_code=200,
    )
    api = Expectativas()
    ep = api.get_endpoint("ExpectativasMercadoAnuais")
    result = ep.get(limit=1, output="text")
    assert isinstance(result, str)
    assert "IPCA" in result


def test_collect_output_dataframe_is_default(httpx_mock):
    """The default output is still a DataFrame when output is not specified."""
    add_service_mocks(httpx_mock)
    httpx_mock.add_response(
        url=ENTITY_URL_PATTERN,
        text=ODATA_QUERY_RESPONSE_JSON,
        status_code=200,
    )
    api = Expectativas()
    ep = api.get_endpoint("ExpectativasMercadoAnuais")
    result = ep.query().limit(1).collect()
    assert isinstance(result, pd.DataFrame)
