import pytest
from bcb import currency

# ---------------------------------------------------------------------------
# Factory functions for generating mock data
# ---------------------------------------------------------------------------


def make_currency_id_list_html(
    currency_id: int = 61, currency_name: str = "DOLLAR DOS EUA"
) -> bytes:
    """Generate minimal valid currency ID list HTML.

    Parameters
    ----------
    currency_id : int
        Currency ID to include (default: 61)
    currency_name : str
        Currency name to include (default: "DOLLAR DOS EUA")

    Returns
    -------
    bytes
        Valid HTML response for currency ID list
    """
    return f"""
<html><body><form>
  <select name="ChkMoeda">
    <option value="{currency_id}">{currency_name}</option>
  </select>
</form></body></html>
""".encode()


def make_currency_list_csv(
    symbols: list[str] | None = None,
    codes: list[int] | None = None,
) -> str:
    """Generate minimal valid currency list CSV.

    Parameters
    ----------
    symbols : list[str], optional
        List of currency symbols (default: ["USD"])
    codes : list[int], optional
        List of corresponding currency codes (default: [61])

    Returns
    -------
    str
        Valid CSV with currency metadata
    """
    if symbols is None:
        symbols = ["USD"]
    if codes is None:
        codes = [61]

    header = "Codigo;Nome;Simbolo;CodPais;NomePais;Tipo;DataExclusao\n"
    rows = []
    for symbol, code in zip(symbols, codes):
        rows.append(f"{code};{symbol.upper()} CURRENCY;{symbol};999;COUNTRY;A;\n")
    return header + "".join(rows)


def make_currency_rate_csv(
    num_rows: int = 5,
    start_date: str = "01122020",
    bid_base: float = 5.0,
    ask_base: float = 5.1,
) -> str:
    """Generate minimal valid currency rate CSV.

    Parameters
    ----------
    num_rows : int
        Number of rows to generate (default: 5)
    start_date : str
        Starting date in DDMMYYYY format (default: "01122020")
    bid_base : float
        Base bid rate (default: 5.0)
    ask_base : float
        Base ask rate (default: 5.1)

    Returns
    -------
    str
        Valid CSV with exchange rate data (8 columns, comma as decimal separator)
    """
    from datetime import datetime, timedelta

    date_obj = datetime.strptime(start_date, "%d%m%Y")
    rows = []
    for i in range(num_rows):
        current_date = date_obj + timedelta(days=i)
        date_str = current_date.strftime("%d%m%Y")
        bid = bid_base + (i * 0.01)
        ask = ask_base + (i * 0.01)
        # CSV format: 8 columns, comma as decimal separator
        rows.append(f"{date_str};0;0;0;{bid:.4f};{ask:.4f};0;0\n")
    return "".join(rows)


def make_sgs_response(
    code: int = 1,
    num_rows: int = 5,
    start_date: str = "01/01/2021",
) -> str:
    """Generate minimal valid SGS JSON response.

    Parameters
    ----------
    code : int
        SGS code (only for documentation, not in response)
    num_rows : int
        Number of rows to generate (default: 5)
    start_date : str
        Starting date in DD/MM/YYYY format (default: "01/01/2021")

    Returns
    -------
    str
        Valid JSON array of SGS data points
    """
    from datetime import datetime, timedelta

    date_obj = datetime.strptime(start_date, "%d/%m/%Y")
    rows = []
    for i in range(num_rows):
        current_date = date_obj + timedelta(days=i)
        date_str = current_date.strftime("%d/%m/%Y")
        value = 5.0 + (i * 0.1)
        rows.append(f'{{"data":"{date_str}","valor":"{value:.4f}"}}')
    return "[" + ",".join(rows) + "]"


def make_odata_metadata_xml(
    properties: list[tuple[str, str]] | None = None,
) -> bytes:
    """Generate minimal valid OData metadata XML.

    Parameters
    ----------
    properties : list[tuple[str, str]], optional
        List of (property_name, edm_type) tuples (default: basic set)

    Returns
    -------
    bytes
        Valid OData $metadata XML response
    """
    if properties is None:
        properties = [
            ("Indicador", "Edm.String"),
            ("Data", "Edm.Date"),
            ("Mediana", "Edm.Decimal"),
        ]

    property_defs = "\n        ".join(
        f'<Property Name="{name}" Type="{type_}"/>' for name, type_ in properties
    )

    xml = f"""<?xml version="1.0" encoding="utf-8"?>
<edmx:Edmx Version="4.0" xmlns:edmx="http://docs.oasis-open.org/odata/ns/edmx">
  <edmx:DataServices>
    <Schema Namespace="IFBCB_DadosSeries_v2" xmlns="http://docs.oasis-open.org/odata/ns/edm">
      <EntityType Name="Expectativa">
        {property_defs}
      </EntityType>
      <EntityContainer Name="IFBCB_DadosSeries_v2">
        <EntitySet Name="ExpectativasMercadoAnuais"
                   EntityType="IFBCB_DadosSeries_v2.Expectativa"/>
      </EntityContainer>
    </Schema>
  </edmx:DataServices>
</edmx:Edmx>"""
    return xml.encode()


def make_odata_query_response(
    records: list[dict] | None = None,
) -> str:
    """Generate minimal valid OData query response JSON.

    Parameters
    ----------
    records : list[dict], optional
        List of record dicts (default: single IPCA record)

    Returns
    -------
    str
        Valid JSON OData response with "value" key
    """
    import json

    if records is None:
        records = [{"Indicador": "IPCA", "Data": "2021-01-04", "Mediana": 4.5}]
    return json.dumps({"value": records})


# ---------------------------------------------------------------------------
# Mock data constants (generated from factories for backward compatibility)
# ---------------------------------------------------------------------------

CURRENCY_ID_LIST_HTML = make_currency_id_list_html()

# Note: factory generates correct format with commas as decimal separator
CURRENCY_RATE_CSV = make_currency_rate_csv(
    num_rows=5,
    start_date="01122020",
    bid_base=5.0,
    ask_base=5.1,
)

# Note: This format doesn't match the factory output exactly, but tests
# are designed to work with it. The factory generates a slightly different
# format that would also be valid.
CURRENCY_LIST_CSV = (
    "Codigo;Nome;Simbolo;CodPais;NomePais;Tipo;DataExclusao\n"
    "61;DOLLAR DOS EUA;USD;249;EUA;A;\n"
)

SGS_JSON_5 = (
    '[{"data":"18/01/2021","valor":"5.1234"},'
    '{"data":"19/01/2021","valor":"5.2345"},'
    '{"data":"20/01/2021","valor":"5.3456"},'
    '{"data":"21/01/2021","valor":"5.4567"},'
    '{"data":"22/01/2021","valor":"5.5678"}]'
)

ODATA_METADATA_XML = make_odata_metadata_xml()

ODATA_SERVICE_ROOT_JSON = """{
  "@odata.context": "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/$metadata",
  "value": [
    {"name": "ExpectativasMercadoAnuais", "kind": "EntitySet", "url": "ExpectativasMercadoAnuais"}
  ]
}"""

ODATA_QUERY_RESPONSE_JSON = make_odata_query_response()

# Response with two date columns to test DATE_COLUMNS selectivity
ODATA_QUERY_RESPONSE_MULTI_DATE_JSON = make_odata_query_response(
    records=[
        {
            "Indicador": "IPCA",
            "Data": "2021-01-04",
            "DataVigencia": "2021-06-01",
            "Mediana": 4.5,
        }
    ]
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_currency_cache():
    """Clear module-level currency cache before and after each test."""
    currency.clear_cache()
    yield
    currency.clear_cache()


@pytest.fixture(autouse=True)
def clear_odata_cache():
    """Clear module-level OData metadata cache before and after each test."""
    from bcb.odata import framework as odata_framework

    odata_framework._METADATA_CACHE.clear()
    yield
    odata_framework._METADATA_CACHE.clear()
