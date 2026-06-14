import re
from datetime import date, datetime

import httpx
import pandas as pd
import pytest

from bcb.odata.api import Expectativas
from bcb.odata.framework import (
    ODataParameter,
    ODataProperty,
    ODataPropertyFilter,
    ODataPropertyOrderBy,
    ODataService,
    str_types,
)
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
FUNCTION_METADATA_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<edmx:Edmx Version="4.0" xmlns:edmx="http://docs.oasis-open.org/odata/ns/edmx">
  <edmx:DataServices>
    <Schema Namespace="TestModel" xmlns="http://docs.oasis-open.org/odata/ns/edm">
      <EntityType Name="Cotacao">
        <Property Name="Moeda" Type="Edm.String"/>
        <Property Name="Data" Type="Edm.Date"/>
        <Property Name="CotacaoCompra" Type="Edm.Decimal"/>
      </EntityType>
      <Function Name="CotacaoMoedaPeriodo">
        <Parameter Name="moeda" Type="Edm.String" Nullable="false"/>
        <Parameter Name="dataInicial" Type="Edm.String" Nullable="false"/>
        <Parameter Name="limite" Type="Edm.Int32" Nullable="false"/>
        <ReturnType Type="Collection(TestModel.Cotacao)"/>
      </Function>
      <EntityContainer Name="Container">
        <EntitySet Name="CotacoesMoedaPeriodo" EntityType="TestModel.Cotacao"/>
        <FunctionImport Name="CotacaoMoedaPeriodo"
                        Function="TestModel.CotacaoMoedaPeriodo"
                        EntitySet="TestModel.CotacoesMoedaPeriodo"/>
      </EntityContainer>
    </Schema>
  </edmx:DataServices>
</edmx:Edmx>"""

FUNCTION_SERVICE_ROOT_JSON = """{
  "@odata.context": "https://example.test/odata/$metadata",
  "value": [
    {"name": "CotacaoMoedaPeriodo", "kind": "FunctionImport", "url": "CotacaoMoedaPeriodo"}
  ]
}"""

FUNCTION_BASE_URL = "https://example.test/odata/"
FUNCTION_METADATA_URL = "https://example.test/odata/$metadata"
FUNCTION_URL_PATTERN = re.compile(r".*CotacaoMoedaPeriodo.*")


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


def add_function_service_mocks(httpx_mock):
    httpx_mock.add_response(
        url=FUNCTION_BASE_URL,
        text=FUNCTION_SERVICE_ROOT_JSON,
        status_code=200,
    )
    httpx_mock.add_response(
        url=FUNCTION_METADATA_URL,
        content=FUNCTION_METADATA_XML,
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


def test_service_root_status_error_raises_odata_error(httpx_mock):
    httpx_mock.add_response(
        url=EXPECTATIVAS_BASE_URL,
        text="service unavailable",
        status_code=503,
    )

    with pytest.raises(ODataError, match="OData service"):
        Expectativas()


def test_service_root_connection_error_raises_odata_error(httpx_mock):
    httpx_mock.add_exception(
        httpx.ConnectError("network down"),
        url=EXPECTATIVAS_BASE_URL,
    )

    with pytest.raises(ODataError, match="OData service"):
        Expectativas()


def test_service_root_malformed_json_raises_odata_error(httpx_mock):
    httpx_mock.add_response(
        url=EXPECTATIVAS_BASE_URL,
        text="not json",
        status_code=200,
    )

    with pytest.raises(ODataError, match="OData service.*invalid JSON"):
        Expectativas()


def test_service_root_missing_required_fields_raises_odata_error(httpx_mock):
    httpx_mock.add_response(
        url=EXPECTATIVAS_BASE_URL,
        text="{}",
        status_code=200,
    )

    with pytest.raises(ODataError, match="missing required field 'value'"):
        Expectativas()


def test_service_root_value_must_be_list(httpx_mock):
    httpx_mock.add_response(
        url=EXPECTATIVAS_BASE_URL,
        text=(
            '{"@odata.context": "'
            + EXPECTATIVAS_METADATA_URL
            + '", "value": {"name": "ExpectativasMercadoAnuais"}}'
        ),
        status_code=200,
    )

    with pytest.raises(ODataError, match="value.*list"):
        Expectativas()


def test_service_root_value_items_must_be_objects(httpx_mock):
    httpx_mock.add_response(
        url=EXPECTATIVAS_BASE_URL,
        text='{"@odata.context": "'
        + EXPECTATIVAS_METADATA_URL
        + '", "value": ["bad"]}',
        status_code=200,
    )

    with pytest.raises(ODataError, match="value.*objects"):
        Expectativas()


def test_service_root_context_must_be_string(httpx_mock):
    httpx_mock.add_response(
        url=EXPECTATIVAS_BASE_URL,
        text='{"@odata.context": 123, "value": []}',
        status_code=200,
    )

    with pytest.raises(ODataError, match="@odata.context.*string"):
        Expectativas()


def test_metadata_status_error_raises_odata_error(httpx_mock):
    httpx_mock.add_response(
        url=EXPECTATIVAS_BASE_URL,
        text=ODATA_SERVICE_ROOT_JSON,
        status_code=200,
    )
    httpx_mock.add_response(
        url=EXPECTATIVAS_METADATA_URL,
        text="metadata unavailable",
        status_code=404,
    )

    with pytest.raises(ODataError, match="OData metadata"):
        Expectativas()


def test_metadata_malformed_xml_raises_odata_error(httpx_mock):
    httpx_mock.add_response(
        url=EXPECTATIVAS_BASE_URL,
        text=ODATA_SERVICE_ROOT_JSON,
        status_code=200,
    )
    httpx_mock.add_response(
        url=EXPECTATIVAS_METADATA_URL,
        text="<edmx:Edmx><bad",
        status_code=200,
    )

    with pytest.raises(ODataError, match="OData metadata.*invalid XML"):
        Expectativas()


def test_metadata_missing_schema_raises_odata_error(httpx_mock):
    httpx_mock.add_response(
        url=EXPECTATIVAS_BASE_URL,
        text=ODATA_SERVICE_ROOT_JSON,
        status_code=200,
    )
    httpx_mock.add_response(
        url=EXPECTATIVAS_METADATA_URL,
        text='<?xml version="1.0"?><root />',
        status_code=200,
    )

    with pytest.raises(ODataError, match="OData metadata.*missing schema"):
        Expectativas()


def test_metadata_invalid_structure_raises_odata_error(httpx_mock):
    httpx_mock.add_response(
        url=EXPECTATIVAS_BASE_URL,
        text=ODATA_SERVICE_ROOT_JSON,
        status_code=200,
    )
    httpx_mock.add_response(
        url=EXPECTATIVAS_METADATA_URL,
        text="""<?xml version="1.0"?>
<edmx:Edmx Version="4.0" xmlns:edmx="http://docs.oasis-open.org/odata/ns/edmx">
  <edmx:DataServices>
    <Schema xmlns="http://docs.oasis-open.org/odata/ns/edm"/>
  </edmx:DataServices>
</edmx:Edmx>""",
        status_code=200,
    )

    with pytest.raises(ODataError, match="invalid structure"):
        Expectativas()


def test_service_reuses_cached_metadata(httpx_mock):
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
    httpx_mock.add_response(
        url=EXPECTATIVAS_BASE_URL,
        text=ODATA_SERVICE_ROOT_JSON,
        status_code=200,
    )

    first = Expectativas()
    second = Expectativas()

    assert second.service.metadata is first.service.metadata


def test_query_status_error_raises_odata_error(httpx_mock):
    add_service_mocks(httpx_mock)
    httpx_mock.add_response(
        url=ENTITY_URL_PATTERN,
        text="too many requests",
        status_code=429,
    )

    api = Expectativas()
    ep = api.get_endpoint("ExpectativasMercadoAnuais")

    with pytest.raises(ODataError, match="rate limit"):
        ep.query().limit(1).collect()


def test_query_malformed_json_raises_odata_error(httpx_mock):
    add_service_mocks(httpx_mock)
    httpx_mock.add_response(
        url=ENTITY_URL_PATTERN,
        text="not json",
        status_code=200,
    )

    api = Expectativas()
    ep = api.get_endpoint("ExpectativasMercadoAnuais")

    with pytest.raises(ODataError, match="OData query.*invalid JSON"):
        ep.query().limit(1).collect()


def test_query_missing_value_raises_odata_error(httpx_mock):
    add_service_mocks(httpx_mock)
    httpx_mock.add_response(
        url=ENTITY_URL_PATTERN,
        text='{"unexpected": []}',
        status_code=200,
    )

    api = Expectativas()
    ep = api.get_endpoint("ExpectativasMercadoAnuais")

    with pytest.raises(ODataError, match="missing required field 'value'"):
        ep.query().limit(1).collect()


def test_query_transport_error_raises_odata_error(httpx_mock):
    add_service_mocks(httpx_mock)
    httpx_mock.add_exception(
        httpx.ConnectError("network down"),
        url=ENTITY_URL_PATTERN,
    )

    api = Expectativas()
    ep = api.get_endpoint("ExpectativasMercadoAnuais")

    with pytest.raises(ODataError, match="OData query.*network down"):
        ep.query().limit(1).text()


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


def test_string_property_filter_escapes_apostrophes():
    indicador = ODataProperty(Name="Indicador", Type="Edm.String")
    assert str(indicador == "Focus's IPCA") == "Indicador eq 'Focus''s IPCA'"


def test_decimal_property_comparison_filters(httpx_mock):
    add_service_mocks(httpx_mock)
    api = Expectativas()
    ep = api.get_endpoint("ExpectativasMercadoAnuais")
    mediana = ep.Mediana
    assert str(mediana > 4.0) == "Mediana gt 4.0"
    assert str(mediana >= 4.0) == "Mediana ge 4.0"
    assert str(mediana < 4.0) == "Mediana lt 4.0"
    assert str(mediana <= 4.0) == "Mediana le 4.0"


def test_date_property_filter_formats_dates():
    data = ODataProperty(Name="Data", Type="Edm.Date")
    assert str(data == date(2024, 1, 31)) == "Data eq 2024-01-31"


def test_int_property_filter_formats_ints():
    prazo = ODataProperty(Name="Prazo", Type="Edm.Int32")
    assert str(prazo == "12") == "Prazo eq 12"


def test_boolean_property_filter_formats_booleans():
    ativo = ODataProperty(Name="Ativo", Type="Edm.Boolean")
    assert str(ativo == True) == "Ativo eq true"  # noqa: E712


@pytest.mark.parametrize(
    ("prop", "value", "message"),
    [
        (ODataProperty(Name="Indicador", Type="Edm.String"), None, "Edm.String"),
        (
            ODataProperty(Name="Mediana", Type="Edm.Decimal"),
            "not-a-number",
            "Edm.Decimal",
        ),
        (ODataProperty(Name="Data", Type="Edm.Date"), "2024-01-31", "Edm.Date"),
        (ODataProperty(Name="Codigo", Type="Edm.Guid"), "abc", "Unsupported"),
    ],
)
def test_property_filter_invalid_values_raise_odata_error(prop, value, message):
    with pytest.raises(ODataError, match=message):
        str(ODataPropertyFilter(prop, value, "eq"))


def test_property_orderby(httpx_mock):
    add_service_mocks(httpx_mock)
    api = Expectativas()
    ep = api.get_endpoint("ExpectativasMercadoAnuais")
    assert isinstance(ep.Mediana.asc(), ODataPropertyOrderBy)
    assert str(ep.Mediana.asc()) == "Mediana asc"
    assert str(ep.Mediana.desc()) == "Mediana desc"


def test_parameter_formatting_and_type_mapping():
    decimal_param = ODataParameter(Name="valor", Type="Edm.Decimal")
    int_param = ODataParameter(Name="prazo", Type="Edm.Int32", Nullable="false")
    string_param = ODataParameter(Name="moeda", Type="Edm.String", Nullable="true")
    bool_param = ODataParameter(Name="ativo", Type="Edm.Boolean")

    assert decimal_param.format("1.25") == "1.25"
    assert int_param.format("12") == "12"
    assert string_param.format("USD") == "'USD'"
    assert bool_param.format(True) == "'True'"
    assert int_param.required
    assert not string_param.required
    assert str_types("Edm.TimeOfDay") == "datetime"
    assert str_types("Edm.Guid") == "Edm.Guid"


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


def test_query_serializes_filter_orderby_select_and_pagination(httpx_mock):
    add_service_mocks(httpx_mock)
    httpx_mock.add_response(
        url=ENTITY_URL_PATTERN,
        text=ODATA_QUERY_RESPONSE_JSON,
        status_code=200,
    )
    api = Expectativas()
    entity = api.service["ExpectativasMercadoAnuais"]

    query = (
        api.service.query(entity)
        .filter(entity.Indicador == "Focus's IPCA", entity.Mediana > 4)
        .orderby(entity.Data.desc())
        .select(entity.Indicador, entity.Mediana)
        .limit(5)
        .skip(10)
    )
    data = query.collect()

    request = httpx_mock.get_requests()[-1]
    assert data["value"][0]["Indicador"] == "IPCA"
    assert request.url.params["$format"] == "json"
    assert (
        request.url.params["$filter"]
        == "Indicador eq 'Focus''s IPCA' and Mediana gt 4.0"
    )
    assert request.url.params["$orderby"] == "Data desc"
    assert request.url.params["$select"] == "Indicador,Mediana"
    assert request.url.params["$top"] == "5"
    assert request.url.params["$skip"] == "10"


def test_query_reset_clears_filters_ordering_and_pagination(httpx_mock):
    add_service_mocks(httpx_mock)
    api = Expectativas()
    entity = api.service["ExpectativasMercadoAnuais"]
    query = (
        api.service.query(entity)
        .filter(entity.Indicador == "IPCA")
        .orderby(entity.Data.asc())
        .limit(5)
    )

    query.reset()

    assert query._build_parameters() == {"$format": "json"}


def test_function_import_query_serialization(httpx_mock):
    add_function_service_mocks(httpx_mock)
    httpx_mock.add_response(
        url=FUNCTION_URL_PATTERN,
        text=ODATA_QUERY_RESPONSE_JSON,
        status_code=200,
    )
    service = ODataService(FUNCTION_BASE_URL)
    function_import = service["CotacaoMoedaPeriodo"]

    result = (
        service.query(function_import)
        .parameters(moeda="USD", dataInicial="01-01-2020", limite=5)
        .limit(1)
        .text()
    )

    request = httpx_mock.get_requests()[-1]
    assert "IPCA" in result
    assert (
        str(request.url).split("?", 1)[0]
        == "https://example.test/odata/CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,limite=@limite)"
    )
    assert request.url.params["@moeda"] == "'USD'"
    assert request.url.params["@dataInicial"] == "'01-01-2020'"
    assert request.url.params["@limite"] == "5"
    assert request.url.params["$top"] == "1"


def test_function_import_missing_required_parameter_raises(httpx_mock):
    add_function_service_mocks(httpx_mock)
    service = ODataService(FUNCTION_BASE_URL)

    with pytest.raises(ODataError, match="Parameter not set: moeda"):
        service.query(service["CotacaoMoedaPeriodo"]).text()


def test_function_import_unknown_parameter_raises(httpx_mock):
    add_function_service_mocks(httpx_mock)
    service = ODataService(FUNCTION_BASE_URL)

    with pytest.raises(ODataError, match="Unknown parameter"):
        service.query(service["CotacaoMoedaPeriodo"]).parameters(unknown="x")


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
