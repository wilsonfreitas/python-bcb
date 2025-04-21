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


def test_get_long_series_error():
    # Test for error when getting long series
    try:
        sgs.get(1, start="2000-01-01", end="2023-01-01")
    except Exception as e:
        assert (
            str(e)
            == "Download error: O sistema aceita uma janela de consulta de, no máximo, 10 anos em séries de periodicidade diária"
        )
    else:
        assert False, "Expected an exception but none was raised."


def test_json_return():
    # Test for JSON return
    x = sgs.get_json(1, last=10)
    assert isinstance(x, str)
    assert len(x) > 0
    assert x.startswith("[")
    assert x.endswith("]")


def test_json_return_long_series_error():
    # Test for JSON return long series error
    try:
        sgs.get_json(1, start="2000-01-01", end="2023-01-01")
    except Exception as e:
        assert (
            str(e)
            == "BCB error: O sistema aceita uma janela de consulta de, no máximo, 10 anos em séries de periodicidade diária"
        )
    else:
        assert False, "Expected an exception but none was raised."

    try:
        sgs.get_json(1, last=50)
    except Exception as e:
        assert (
            str(e)
            == "BCB error: br.gov.bcb.pec.sgs.comum.excecoes.SGSNegocioException: A quantidade máxima de valores deve ser 20"
        )
    else:
        assert False, "Expected an exception but none was raised."
