import json

import pytest
from bcb import currency

# ---------------------------------------------------------------------------
# Mock data constants
# ---------------------------------------------------------------------------

# OData /Moedas response
CURRENCY_LIST_JSON = json.dumps(
    {
        "value": [
            {"simbolo": "USD", "nomeFormatado": "DOLLAR DOS EUA", "tipoMoeda": "A"},
        ]
    }
)

# OData /CotacaoMoedaPeriodo response — one "Fechamento" bulletin per trading day
CURRENCY_RATE_ODATA_JSON = json.dumps(
    {
        "value": [
            {
                "cotacaoCompra": 5.0000,
                "cotacaoVenda": 5.1000,
                "dataHoraCotacao": "2020-12-01 13:03:38.273",
                "tipoBoletim": "Fechamento",
            },
            {
                "cotacaoCompra": 5.0100,
                "cotacaoVenda": 5.1100,
                "dataHoraCotacao": "2020-12-02 13:03:38.273",
                "tipoBoletim": "Fechamento",
            },
            {
                "cotacaoCompra": 5.0200,
                "cotacaoVenda": 5.1200,
                "dataHoraCotacao": "2020-12-03 13:03:38.273",
                "tipoBoletim": "Fechamento",
            },
            {
                "cotacaoCompra": 5.0300,
                "cotacaoVenda": 5.1300,
                "dataHoraCotacao": "2020-12-04 13:03:38.273",
                "tipoBoletim": "Fechamento",
            },
            {
                "cotacaoCompra": 5.0400,
                "cotacaoVenda": 5.1400,
                "dataHoraCotacao": "2020-12-07 13:03:38.273",
                "tipoBoletim": "Fechamento",
            },
        ]
    }
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
