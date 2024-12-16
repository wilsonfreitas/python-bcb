import pandas as pd
import pytest
from bcb.sgs.regional_economy import get_non_performing_loans, get_non_performing_loans_codes


class TestGetNonPerformingLoansCodes:
    @pytest.mark.parametrize("states,expected_codes", [
        (["ba", "pa"], ["15865", "15938"]),
        (["BA"], ["15865"]),
        ("N", ["15952"]),
    ])
    def test_get_non_performing_loans_codes_by_state_total(self, states, expected_codes):
        assert get_non_performing_loans_codes(states) == expected_codes


class TestGetNonPerformingLoans:
    @pytest.mark.parametrize("states,expected_columns", [
        (["BA"], ["15865"]),
        (["ba"], ["15865"]),
        ("N", ["15888"]),
    ])
    def test_get_series_by_states_pf(self, states, expected_columns):
        series = get_non_performing_loans(states, last=10, mode="pf")
        assert isinstance(series, pd.DataFrame)
        assert series.columns == expected_columns
        assert len(series) == 10
