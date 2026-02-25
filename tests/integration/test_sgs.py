"""Integration tests for bcb.sgs — require live BCB network access."""
from datetime import datetime

import pandas as pd
import pytest

from bcb import sgs


@pytest.mark.integration
def test_get_series():
    x = sgs.get(1, last=10)
    assert isinstance(x, pd.DataFrame)
    assert x.columns.tolist() == ["1"]
    assert len(x) == 10

    x = sgs.get({"USDBRL": 1}, last=5)
    assert isinstance(x, pd.DataFrame)
    assert x.columns.tolist() == ["USDBRL"]
    assert len(x) == 5

    x = sgs.get({"USDBRL": 1}, start="2021-01-18", end="2021-01-22")
    assert isinstance(x, pd.DataFrame)
    assert x.columns.tolist() == ["USDBRL"]
    assert len(x) == 5
    assert x.index[0] == datetime.strptime("2021-01-18", "%Y-%m-%d")
    assert x.index[-1] == datetime.strptime("2021-01-22", "%Y-%m-%d")


@pytest.mark.integration
def test_json_return():
    x = sgs.get_json(1, last=10)
    assert isinstance(x, str)
    assert len(x) > 0
    assert x.startswith("[")
    assert x.endswith("]")


@pytest.mark.integration
def test_json_return_long_series_error():
    try:
        sgs.get_json(1, start="2000-01-01", end="2023-01-01")
    except Exception as e:
        assert "no máximo" in str(e)
    else:
        assert False, "Expected an exception but none was raised."

    try:
        sgs.get_json(1, last=50)
    except Exception as e:
        assert "máxima" in str(e)
    else:
        assert False, "Expected an exception but none was raised."
