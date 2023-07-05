from datetime import datetime
import pandas as pd
from bcb import sgs


def test_series_code_args():
    code = sgs.SGSCode(1)
    assert code.name == "1"
    assert code.value == 1

    code = sgs.SGSCode("1")
    assert code.name == "1"
    assert code.value == 1

    code = sgs.SGSCode(1, "name")
    assert code.name == "name"
    assert code.value == 1


def test_series_code_iter():
    x = list(sgs._codes(None))
    assert len(x) == 0

    x = list(sgs._codes(1))
    assert len(x) == 1
    assert isinstance(x[0], sgs.SGSCode)
    assert x[0].name == "1"
    assert x[0].value == 1

    x = list(sgs._codes("1"))
    assert len(x) == 1
    assert isinstance(x[0], sgs.SGSCode)
    assert x[0].name == "1"
    assert x[0].value == 1

    x = list(sgs._codes([1, 2]))
    assert len(x) == 2
    assert isinstance(x[0], sgs.SGSCode)
    assert x[0].name == "1"
    assert x[0].value == 1
    assert x[1].name == "2"
    assert x[1].value == 2

    x = list(sgs._codes(("name", 1)))
    assert len(x) == 1
    assert isinstance(x[0], sgs.SGSCode)
    assert x[0].name == "name"
    assert x[0].value == 1

    x = list(sgs._codes([("name", 1), 2]))
    assert len(x) == 2
    assert isinstance(x[0], sgs.SGSCode)
    assert x[0].name == "name"
    assert x[0].value == 1
    assert x[1].name == "2"
    assert x[1].value == 2

    x = list(sgs._codes({"1": 1}))
    assert len(x) == 1
    assert isinstance(x[0], sgs.SGSCode)
    assert x[0].name == "1"
    assert x[0].value == 1

    x = list(sgs._codes({"name1": 1, "name2": 2}))
    assert len(x) == 2
    assert isinstance(x[0], sgs.SGSCode)
    assert x[0].name == "name1"
    assert x[0].value == 1
    assert x[1].name == "name2"
    assert x[1].value == 2


def test_get_series():
    x = sgs.get(1, last=10)
    assert isinstance(x, pd.DataFrame)
    assert x.columns == ["1"]
    assert len(x) == 10

    x = sgs.get({"USDBRL": 1}, last=5)
    assert isinstance(x, pd.DataFrame)
    assert x.columns == ["USDBRL"]
    assert len(x) == 5

    x = sgs.get({"USDBRL": 1}, start="2021-01-18", end="2021-01-22")
    assert isinstance(x, pd.DataFrame)
    assert x.columns == ["USDBRL"]
    assert len(x) == 5
    assert x.index[0] == datetime.strptime("2021-01-18", "%Y-%m-%d")
    assert x.index[-1] == datetime.strptime("2021-01-22", "%Y-%m-%d")
