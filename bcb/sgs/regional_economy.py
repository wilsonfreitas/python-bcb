from typing import Dict, List, Optional, Union

import pandas as pd

from bcb.sgs import get
from bcb.utils import DateInput

"""
Dados da Economia Regional

Histórico de taxas de inadimplência das operações de crédito do Sistema Financeiro Nacional para
pessoas físicas e pessoas jurídicas.

Dados disponíveis por região e por estado.
"""

NON_PERFORMING_LOANS_BY_REGION_PF = {
    "N": "15888",
    "NE": "15889",
    "CO": "15890",
    "SE": "15891",
    "S": "15892",
}
NON_PERFORMING_LOANS_BY_STATE_PF = {
    "AC": "15861",
    "AL": "15862",
    "AP": "15863",
    "AM": "15864",
    "BA": "15865",
    "CE": "15866",
    "DF": "15867",
    "ES": "15868",
    "GO": "15869",
    "MA": "15870",
    "MT": "15871",
    "MS": "15872",
    "MG": "15873",
    "PA": "15874",
    "PB": "15875",
    "PR": "15876",
    "PE": "15877",
    "PI": "15878",
    "RJ": "15879",
    "RN": "15880",
    "RS": "15881",
    "RO": "15882",
    "RR": "15883",
    "SC": "15884",
    "SP": "15885",
    "SE": "15886",
    "TO": "15887",
}
NON_PERFORMING_LOANS_BY_REGION_PJ = {
    "N": "15920",
    "NE": "15921",
    "CO": "15922",
    "SE": "15923",
    "S": "15924",
}
NON_PERFORMING_LOANS_BY_STATE_PJ = {
    "AC": "15893",
    "AL": "15894",
    "AP": "15895",
    "AM": "15896",
    "BA": "15897",
    "CE": "15898",
    "DF": "15899",
    "ES": "15900",
    "GO": "15901",
    "MA": "15902",
    "MT": "15903",
    "MS": "15904",
    "MG": "15905",
    "PA": "15906",
    "PB": "15907",
    "PR": "15908",
    "PE": "15909",
    "PI": "15910",
    "RJ": "15911",
    "RN": "15912",
    "RS": "15913",
    "RO": "15914",
    "RR": "15915",
    "SC": "15916",
    "SP": "15917",
    "SE": "15918",
    "TO": "15919",
}
NON_PERFORMING_LOANS_BY_REGION_TOTAL = {
    "N": "15952",
    "NE": "15953",
    "CO": "15954",
    "SE": "15955",
    "S": "15956",
}
NON_PERFORMING_LOANS_BY_STATE_TOTAL = {
    "AC": "15925",
    "AL": "15926",
    "AP": "15927",
    "AM": "15928",
    "BA": "15929",
    "CE": "15930",
    "DF": "15931",
    "ES": "15932",
    "GO": "15933",
    "MA": "15934",
    "MT": "15935",
    "MS": "15936",
    "MG": "15937",
    "PA": "15938",
    "PB": "15939",
    "PR": "15940",
    "PE": "15941",
    "PI": "15942",
    "RJ": "15943",
    "RN": "15944",
    "RS": "15945",
    "RO": "15946",
    "RR": "15947",
    "SC": "15948",
    "SP": "15949",
    "SE": "15950",
    "TO": "15951",
}


def get_non_performing_loans_codes(states_or_region: Union[str, List[str]], mode: str = "total") -> Dict[str, str]:
    is_state = False
    is_region = False
    states_or_region = [states_or_region] if isinstance(states_or_region, str) else states_or_region
    states_or_region = [location.upper() for location in states_or_region]
    if any(location in list(NON_PERFORMING_LOANS_BY_STATE_TOTAL.keys()) for location in states_or_region):
        is_state = True
    elif any(location in list(NON_PERFORMING_LOANS_BY_REGION_TOTAL.keys()) for location in states_or_region):
        is_region = True

    if not is_state and not is_region:
        raise Exception(f"Not a valid state or region: {states_or_region}")

    codes = {}
    non_performing_loans_by_location = NON_PERFORMING_LOANS_BY_STATE_TOTAL
    if is_state:
        if mode.upper() == "PF":
            non_performing_loans_by_location = NON_PERFORMING_LOANS_BY_STATE_PF
        elif mode.upper() == "PJ":
            non_performing_loans_by_location = NON_PERFORMING_LOANS_BY_STATE_PJ
    elif is_region:
        non_performing_loans_by_location = NON_PERFORMING_LOANS_BY_REGION_TOTAL
        if mode.upper() == "PF":
            non_performing_loans_by_location = NON_PERFORMING_LOANS_BY_REGION_PF
        elif mode.upper() == "PJ":
            non_performing_loans_by_location = NON_PERFORMING_LOANS_BY_REGION_PJ

    for location in states_or_region:
        codes[location] = non_performing_loans_by_location[location]
    return codes


def get_non_performing_loans(
    states_or_region: Union[str, List[str]],
    mode: str = "total",
    start: Optional[DateInput] = None,
    end: Optional[DateInput] = None,
    last: int = 0,
    freq: Optional[str] = None,
) -> pd.DataFrame:
    """Dados de inadimplência das operações de crédito.

    Esta função é um *wrapper* para o método para a função ``get`` do módulo ``sgs``,
    simplificando o acesso aos dados de inadimplência das operações de crédito.
    Nessa função o usuário escolhe o tipo de inadimplência, o(s) estado(s) ou as regiões
    que deseja obter os dados.

    >>> from bcb.sgs.regional_economy import get_non_performing_loans
    >>> from bcb.utils import BRAZILIAN_REGIONS
    >>> series = get_non_performing_loans(["RR"], last=10, mode="all")
    >>> northeast_states = BRAZILIAN_REGIONS["NE"]
    >>> series_ne = get_non_performing_loans(northeast_states, last=5, mode="pj")

    Parameters
    ----------

    states_or_region (List[str]): Uma lista com estado ou região.
    mode (str): O tipo de inadimplência. Pode ser "PF" (pessoas físicas),
                "PJ" (pessoas jurídicas) ou "total" (inadimplência total).
    start : str, int, date, datetime, Timestamp
        Data de início da série.
        Interpreta diferentes tipos e formatos de datas.
    end : string, int, date, datetime, Timestamp
        Data final da série.
        Interpreta diferentes tipos e formatos de datas.
    last : int
        Retorna os últimos ``last`` elementos disponíveis da série temporal
        solicitada. Se ``last`` for maior que 0 (zero) os argumentos ``start``
        e ``end`` são ignorados.
    freq : str
        Define a frequência a ser utilizada na série temporal


    Returns
    -------

    ``DataFrame`` :
        série temporal univariada ou multivariada,
        quando solicitado mais de uma série temporal.
    """
    codes = get_non_performing_loans_codes(states_or_region, mode=mode)
    return get(codes, start=start, end=end, last=last, multi=True, freq=freq)
