from bcb.sgs import get
import pandas as pd

NON_PERFORMING_LOANS_BY_REGION_PF = {
    "N": "15888",
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
    "RO": "15882",
    "RR": "15883",
    "SC": "",
    "SP": "",
    "SE": "",
    "TO": "15887",
}
NON_PERFORMING_LOANS_BY_REGION_PJ = {
    "N": "15920",
    "NE": "",
    "CO": "",
    "SE": "",
    "S": "",
}
NON_PERFORMING_LOANS_BY_STATE_PJ = {
    "AC": "15893",
    "AL": "",
    "AP": "15895",
    "AM": "15896",
    "BA": "15865",
    "CE": "",
    "DF": "",
    "ES": "",
    "GO": "",
    "MA": "",
    "MT": "",
    "MS": "",
    "MG": "",
    "PA": "15906",
    "PB": "",
    "PR": "",
    "PE": "",
    "PI": "",
    "RJ": "",
    "RN": "",
    "RS": "",
    "RO": "15914",
    "RR": "15915",
    "SC": "",
    "SP": "",
    "SE": "",
    "TO": "15919"
}
NON_PERFORMING_LOANS_BY_REGION_TOTAL = {
    "N": "15952",
    "NE": "",
    "CO": "",
    "SE": "",
    "S": "",
}
NON_PERFORMING_LOANS_BY_STATE_TOTAL = {
    "AC": "15925",
    "AL": "",
    "AP": "15927",
    "AM": "15928",
    "BA": "15865",
    "CE": "",
    "DF": "",
    "ES": "",
    "GO": "",
    "MA": "",
    "MT": "",
    "MS": "",
    "MG": "",
    "PA": "15938",
    "PB": "",
    "PR": "",
    "PE": "",
    "PI": "",
    "RJ": "",
    "RN": "",
    "RS": "",
    "RO": "15946",
    "RR": "15947",
    "SC": "",
    "SP": "",
    "SE": "",
    "TO": "15951"
}


def get_non_performing_loans_codes(states_or_region, mode="total"):
    """SGS da Inadimplência das operações de crédito.

    Pode ser total, pessoas físicas (PF) ou jurídicas (PJ)."""
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

    codes = []
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
        codes.append(non_performing_loans_by_location[location])
    return codes


def get_non_performing_loans(states_or_region, mode="total", start=None, end=None, last=0, freq=None):
    codes = get_non_performing_loans_codes(states_or_region, mode=mode)
    return get(codes, start=start, end=end, last=last, multi=True, freq=freq)
