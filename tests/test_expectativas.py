import pandas as pd
from datetime import datetime
from pytest import fixture

from bcb import Expectativas


@fixture
def endpoints():
    ep = Expectativas()
    return [ep.get_endpoint(e.data["name"]) for e in ep.service.endpoints]


def test_expectativas_date_format(endpoints):
    for endpoint in endpoints:
        query = endpoint.query().limit(1)
        data = query.collect()
        assert isinstance(data, pd.DataFrame)
        assert data.shape[0] == 1
        assert isinstance(data["Data"].iloc[0], datetime)
