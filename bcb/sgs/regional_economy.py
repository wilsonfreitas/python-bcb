from bcb.sgs import get
import pandas as pd

NON_PERFORMING_LOANS_BY_REGION_PF = {
    "N": "",
    "NE": "",
    "CO": "",
    "SE": "",
    "S": "",
}
NON_PERFORMING_LOANS_BY_STATE_PF = {
    "AC": "15861",
    "AL": "",
    "AP": "15863",
    "AM": "15864",
    "BA": "15865",
    "CE": "",
    "DF": "",
    "ES": "",
    "GO": "",
    "MA": "",
    "MT": "",
    "MS": "",
    "MG": "",
    "PA": "15874",
    "PB": "",
    "PR": "",
    "PE": "",
    "PI": "",
    "RJ": "",
    "RN": "",
    "RS": "",
    "RO": "",
    "RR": "",
    "SC": "",
    "SP": "",
    "SE": "",
    "TO": "",
}
NON_PERFORMING_LOANS_BY_REGION_PJ = {
    "N": "",
    "NE": "",
    "CO": "",
    "SE": "",
    "S": "",
}
NON_PERFORMING_LOANS_BY_STATE_PJ = {
    "AC": "15861",
    "AL": "",
    "AP": "15863",
    "AM": "15864",
    "BA": "15865",
    "CE": "",
    "DF": "",
    "ES": "",
    "GO": "",
    "MA": "",
    "MT": "",
    "MS": "",
    "MG": "",
    "PA": "15874",
    "PB": "",
    "PR": "",
    "PE": "",
    "PI": "",
    "RJ": "",
    "RN": "",
    "RS": "",
    "RO": "",
    "RR": "",
    "SC": "",
    "SP": "",
    "SE": "",
    "TO": ""
}
NON_PERFORMING_LOANS_BY_REGION_TOTAL = {
    "N": "",
    "NE": "",
    "CO": "",
    "SE": "",
    "S": "",
}
NON_PERFORMING_LOANS_BY_STATE_TOTAL = {
    "AC": "15861",
    "AL": "",
    "AP": "15863",
    "AM": "15864",
    "BA": "15865",
    "CE": "",
    "DF": "",
    "ES": "",
    "GO": "",
    "MA": "",
    "MT": "",
    "MS": "",
    "MG": "",
    "PA": "15874",
    "PB": "",
    "PR": "",
    "PE": "",
    "PI": "",
    "RJ": "",
    "RN": "",
    "RS": "",
    "RO": "",
    "RR": "",
    "SC": "",
    "SP": "",
    "SE": "",
    "TO": ""
}


def get_non_performing_loans_codes(states_or_region, mode="total"):
    """SGS da Inadimplência das operações de crédito.

    Pode ser total, pessoas físicas (PF) ou jurídicas (PJ)."""
    non_performing_loans_by_state = NON_PERFORMING_LOANS_BY_STATE_TOTAL
    non_performing_loans_by_region = NON_PERFORMING_LOANS_BY_REGION_TOTAL

    is_state = False
    is_region = False
    states_or_region = [states_or_region] if isinstance(states_or_region, str) else states_or_region
    states_or_region = [location.upper() for location in states_or_region]
    if any(location in list(non_performing_loans_by_state.keys()) for location in states_or_region):
        is_state = True
    elif any(location in list(non_performing_loans_by_region.keys()) for location in states_or_region):
        is_region = True

    if not is_state and not is_region:
        raise Exception(f"Not a valid state or region: {states_or_region}")

    codes = []
    if is_state:
        if mode.upper() == "PF":
            non_performing_loans_by_state = NON_PERFORMING_LOANS_BY_STATE_PF
        elif mode.upper() == "PJ":
            non_performing_loans_by_state = NON_PERFORMING_LOANS_BY_STATE_PJ
    elif is_region:
        if mode.upper() == "PF":
            non_performing_loans_by_state = NON_PERFORMING_LOANS_BY_REGION_PF
        elif mode.upper() == "PJ":
            non_performing_loans_by_state = NON_PERFORMING_LOANS_BY_REGION_PJ

    for location in states_or_region:
        codes.append(non_performing_loans_by_state.get(location))
    return codes


def get_non_performing_loans(states_or_region, mode="total", start=None, end=None, last=0, freq=None):
    codes = get_non_performing_loans_codes(states_or_region, mode=mode)
    return get(codes, start=start, end=end, last=last, multi=True, freq=freq)
