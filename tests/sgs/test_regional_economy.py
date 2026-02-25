import pandas as pd
import pytest
from bcb.sgs.regional_economy import get_non_performing_loans, get_non_performing_loans_codes
from bcb.utils import BRAZILIAN_REGIONS, BRAZILIAN_STATES
from bcb.sgs import regional_economy


class TestGetNonPerformingLoansCodes:
    @pytest.mark.parametrize("states,expected_codes", [
        (["ba", "pa"], {"BA": "15929", "PA": "15938"}),
        (["BA"], {"BA": "15929"}),
        ("N", {"N": "15952"}),
    ])
    def test_get_non_performing_loans_codes_by_state_total(self, states, expected_codes):
        assert get_non_performing_loans_codes(states) == expected_codes


@pytest.mark.integration
class TestGetNonPerformingLoans:
    @pytest.mark.parametrize("states,expected_columns", [
        (["BA"], ["BA"]),
        (["am", "pa"], ["AM", "PA"]),
        ("N", ["N"]),
    ])
    def test_get_series_by_states_pf(self, states, expected_columns):
        series = get_non_performing_loans(states, last=10, mode="pf")

        assert isinstance(series, pd.DataFrame)
        assert (series.columns == expected_columns).all()
        assert len(series) == 10

    def test_get_series_by_region_pj(self):
        south_states = BRAZILIAN_REGIONS["S"]
        series = get_non_performing_loans(south_states, last=5, mode="pj")

        assert isinstance(series, pd.DataFrame)
        assert (series.columns == south_states).all()
        assert len(series) == 5


class TestNonPerformingLoansCodes:
    @pytest.fixture
    def non_performing_constants(self):
        constants = [
            item
            for item in dir(regional_economy)
            if item.startswith("NON_PERFORMING_LOANS_BY")
        ]
        return constants

    def test_if_all_regions_and_states_are_there(self, non_performing_constants):
        for item_str in non_performing_constants:
            item = getattr(regional_economy, item_str)
            if "REGION" in str(item):
                assert (list(item.values()) == list(BRAZILIAN_REGIONS.keys())), item_str
            elif "STATE" in str(item):
                assert (list(item.values()) == BRAZILIAN_STATES), item_str

    def test_check_if_codes_are_unique(self, non_performing_constants):
        for item_str in non_performing_constants:
            item = getattr(regional_economy, item_str)

            unique_values = set(item.values())
            assert all(unique_values), item_str
            assert (len(item.values()) == len(unique_values)), item_str
