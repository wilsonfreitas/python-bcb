import pytest
from bcb import currency


# ---------------------------------------------------------------------------
# Mock data constants
# ---------------------------------------------------------------------------

CURRENCY_ID_LIST_HTML = b"""
<html><body><form>
  <select name="ChkMoeda">
    <option value="61">DOLLAR DOS EUA</option>
  </select>
</form></body></html>
"""

# First row is treated as header by pd.read_csv, then overwritten by df.columns = [...]
CURRENCY_LIST_CSV = (
    "Codigo;Nome;Simbolo;CodPais;NomePais;Tipo;DataExclusao\n"
    "61;DOLLAR DOS EUA;USD;249;EUA;A;\n"
)

# 8 columns, no header, date format DDMMYYYY, comma as decimal separator
CURRENCY_RATE_CSV = (
    "01122020;0;0;0;5,0000;5,1000;0;0\n"
    "02122020;0;0;0;5,0100;5,1100;0;0\n"
    "03122020;0;0;0;5,0200;5,1200;0;0\n"
    "04122020;0;0;0;5,0300;5,1300;0;0\n"
    "07122020;0;0;0;5,0400;5,1400;0;0\n"
)

SGS_JSON_5 = (
    '[{"data":"18/01/2021","valor":"5.1234"},'
    '{"data":"19/01/2021","valor":"5.2345"},'
    '{"data":"20/01/2021","valor":"5.3456"},'
    '{"data":"21/01/2021","valor":"5.4567"},'
    '{"data":"22/01/2021","valor":"5.5678"}]'
)

ODATA_METADATA_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<edmx:Edmx Version="4.0" xmlns:edmx="http://docs.oasis-open.org/odata/ns/edmx">
  <edmx:DataServices>
    <Schema Namespace="IFBCB_DadosSeries_v2" xmlns="http://docs.oasis-open.org/odata/ns/edm">
      <EntityType Name="Expectativa">
        <Property Name="Indicador" Type="Edm.String"/>
        <Property Name="Data" Type="Edm.Date"/>
        <Property Name="Mediana" Type="Edm.Decimal"/>
      </EntityType>
      <EntityContainer Name="IFBCB_DadosSeries_v2">
        <EntitySet Name="ExpectativasMercadoAnuais"
                   EntityType="IFBCB_DadosSeries_v2.Expectativa"/>
      </EntityContainer>
    </Schema>
  </edmx:DataServices>
</edmx:Edmx>"""

ODATA_SERVICE_ROOT_JSON = """{
  "@odata.context": "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/$metadata",
  "value": [
    {"name": "ExpectativasMercadoAnuais", "kind": "EntitySet", "url": "ExpectativasMercadoAnuais"}
  ]
}"""

ODATA_QUERY_RESPONSE_JSON = """{
  "value": [
    {"Indicador": "IPCA", "Data": "2021-01-04", "Mediana": 4.5}
  ]
}"""

# Response with two date columns to test DATE_COLUMNS selectivity
ODATA_QUERY_RESPONSE_MULTI_DATE_JSON = """{
  "value": [
    {"Indicador": "IPCA", "Data": "2021-01-04", "DataVigencia": "2021-06-01", "Mediana": 4.5}
  ]
}"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_currency_cache():
    """Clear module-level currency cache before and after each test."""
    currency.clear_cache()
    yield
    currency.clear_cache()
