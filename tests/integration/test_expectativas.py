"""Integration tests for bcb.odata Expectativas — require live BCB network access."""

import pandas as pd
import pytest
from datetime import datetime
from pytest import fixture

from bcb import Expectativas


@fixture
def endpoints():
    ep = Expectativas()
    return [ep.get_endpoint(e.data["name"]) for e in ep.service.endpoints]


@pytest.mark.integration
def test_expectativas_date_format(endpoints):
    date_columns = {
        "Data",
        "dataHoraCotacao",
        "InicioPeriodo",
        "FimPeriodo",
        "DataVigencia",
    }
    for endpoint in endpoints:
        query = endpoint.query().limit(1)
        data = query.collect()
        assert isinstance(data, pd.DataFrame)
        assert data.shape[0] == 1
        for col in date_columns:
            if col in data.columns:
                assert isinstance(data[col].iloc[0], datetime)
