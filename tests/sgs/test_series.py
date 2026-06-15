import re

import pandas as pd
import pytest

from bcb import sgs
from bcb.exceptions import SGSError
from tests.conftest import SGS_JSON_5

SGS_CODE_1_URL = re.compile(
    r".*bcdata\.sgs\.1[^0-9].*|.*bcdata\.sgs\.1$|.*bcdata\.sgs\.1/.*"
)
SGS_CODE_99999_URL = re.compile(r".*bcdata\.sgs\.99999.*")
SGS_CODE_2_URL = re.compile(
    r".*bcdata\.sgs\.2[^0-9].*|.*bcdata\.sgs\.2$|.*bcdata\.sgs\.2/.*"
)


# ---------------------------------------------------------------------------
# Pure unit tests (no HTTP)
# ---------------------------------------------------------------------------


def test_series_code_args():
    code = sgs.SGSCode.from_code(1)
    assert code.name == "1"
    assert code.value == 1

    code = sgs.SGSCode.from_code("1")
    assert code.name == "1"
    assert code.value == 1

    code = sgs.SGSCode.from_named(1, "name")
    assert code.name == "name"
    assert code.value == 1


def test_series_code_repr():
    code = sgs.SGSCode.from_code(1)
    assert repr(code) == "1 - 1"  # name defaults to str(value)

    code = sgs.SGSCode.from_named(1, "SELIC")
    assert repr(code) == "1 - SELIC"


def test_series_code_iter_int():
    x = list(sgs._codes(1))
    assert len(x) == 1
    assert isinstance(x[0], sgs.SGSCode)
    assert x[0].name == "1"
    assert x[0].value == 1


def test_series_code_iter_str():
    x = list(sgs._codes("1"))
    assert len(x) == 1
    assert x[0].name == "1"
    assert x[0].value == 1


def test_series_code_iter_list():
    x = list(sgs._codes([1, 2]))
    assert len(x) == 2
    assert x[0].value == 1
    assert x[1].value == 2


def test_series_code_iter_tuple():
    x = list(sgs._codes(("name", 1)))
    assert len(x) == 1
    assert x[0].name == "name"
    assert x[0].value == 1


def test_series_code_iter_list_of_tuples():
    x = list(sgs._codes([("name", 1), 2]))
    assert len(x) == 2
    assert x[0].name == "name"
    assert x[0].value == 1
    assert x[1].name == "2"
    assert x[1].value == 2


def test_series_code_iter_dict():
    x = list(sgs._codes({"name1": 1, "name2": 2}))
    assert len(x) == 2
    assert x[0].name == "name1"
    assert x[0].value == 1
    assert x[1].name == "name2"
    assert x[1].value == 2


def test_series_code_iter_unknown_type():
    with pytest.raises(ValueError, match="Unsupported SGS code input"):
        list(sgs._codes(None))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Mocked HTTP tests
# ---------------------------------------------------------------------------


def test_get_json_returns_string(httpx_mock):
    httpx_mock.add_response(
        url=SGS_CODE_1_URL,
        text=SGS_JSON_5,
        status_code=200,
    )
    result = sgs.get_json(1, last=5)
    assert isinstance(result, str)
    assert result.startswith("[")
    assert result.endswith("]")


def test_get_returns_dataframe(httpx_mock):
    httpx_mock.add_response(
        url=SGS_CODE_1_URL,
        text=SGS_JSON_5,
        status_code=200,
    )
    df = sgs.get(1, last=5)
    assert isinstance(df, pd.DataFrame)
    assert "1" in df.columns
    assert len(df) == 5


def test_get_with_named_code(httpx_mock):
    httpx_mock.add_response(
        url=SGS_CODE_1_URL,
        text=SGS_JSON_5,
        status_code=200,
    )
    df = sgs.get({"SELIC": 1}, last=5)
    assert isinstance(df, pd.DataFrame)
    assert "SELIC" in df.columns
    assert len(df) == 5


def test_get_tidy_single_code(httpx_mock):
    httpx_mock.add_response(
        url=SGS_CODE_1_URL,
        text=SGS_JSON_5,
        status_code=200,
    )

    df = sgs.get(1, last=5, tidy=True)

    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["Date", "series", "value"]
    assert df["series"].unique().tolist() == ["1"]
    assert len(df) == 5


def test_get_tidy_multiple_codes(httpx_mock):
    httpx_mock.add_response(
        url=SGS_CODE_1_URL,
        text=SGS_JSON_5,
        status_code=200,
    )
    httpx_mock.add_response(
        url=SGS_CODE_2_URL,
        text=SGS_JSON_5,
        status_code=200,
    )

    df = sgs.get([1, 2], last=5, tidy=True)

    assert list(df.columns) == ["Date", "series", "value"]
    assert set(df["series"]) == {"1", "2"}
    assert len(df) == 10


def test_get_tidy_ignores_text_output(httpx_mock):
    httpx_mock.add_response(
        url=SGS_CODE_1_URL,
        text=SGS_JSON_5,
        status_code=200,
    )

    result = sgs.get(1, last=5, output="text", tidy=True)

    assert isinstance(result, str)
    assert result == SGS_JSON_5


def test_get_json_error_response(httpx_mock):
    httpx_mock.add_response(
        url=SGS_CODE_99999_URL,
        text='{"erro": {"detail": "Série não encontrada"}}',
        status_code=400,
    )
    with pytest.raises(SGSError, match="Série não encontrada"):
        sgs.get_json(99999, last=1)


def test_get_json_generic_error_response(httpx_mock):
    httpx_mock.add_response(
        url=SGS_CODE_99999_URL,
        text='{"error": "unknown series"}',
        status_code=400,
    )
    with pytest.raises(SGSError, match="unknown series"):
        sgs.get_json(99999, last=1)


# ---------------------------------------------------------------------------
# output="text" — raw JSON string
# ---------------------------------------------------------------------------


def test_get_output_text_single_code_returns_string(httpx_mock):
    """get(code, output='text') returns the raw JSON string for a single code."""
    httpx_mock.add_response(
        url=SGS_CODE_1_URL,
        text=SGS_JSON_5,
        status_code=200,
    )
    result = sgs.get(1, last=5, output="text")
    assert isinstance(result, str)
    assert result == SGS_JSON_5


def test_get_output_text_multi_code_returns_dict(httpx_mock):
    """get([c1, c2], output='text') returns a dict mapping code → JSON string."""
    SGS_CODE_2_URL = re.compile(
        r".*bcdata\.sgs\.2[^0-9].*|.*bcdata\.sgs\.2$|.*bcdata\.sgs\.2/.*"
    )
    httpx_mock.add_response(
        url=SGS_CODE_1_URL,
        text=SGS_JSON_5,
        status_code=200,
    )
    httpx_mock.add_response(
        url=SGS_CODE_2_URL,
        text=SGS_JSON_5,
        status_code=200,
    )
    result = sgs.get([1, 2], last=5, output="text")
    assert isinstance(result, dict)
    assert 1 in result
    assert 2 in result
    assert isinstance(result[1], str)
    assert isinstance(result[2], str)


def test_get_output_dataframe_is_default(httpx_mock):
    """Default output (no output param) still returns a DataFrame."""
    httpx_mock.add_response(
        url=SGS_CODE_1_URL,
        text=SGS_JSON_5,
        status_code=200,
    )
    result = sgs.get(1, last=5)
    assert isinstance(result, pd.DataFrame)
