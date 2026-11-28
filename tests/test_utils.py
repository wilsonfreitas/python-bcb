import pytest
from datetime import date, datetime

from bcb import utils


def test_date():
    d = utils.Date("2020-01-01")
    assert d.date == date(2020, 1, 1)
    d = utils.Date("01/01/2020", format="%d/%m/%Y")
    assert d.date == date(2020, 1, 1)
    d = utils.Date(date(2020, 1, 1))
    assert d.date == date(2020, 1, 1)
    d = utils.Date(datetime(2020, 1, 1))
    assert d.date == date(2020, 1, 1)
    d = utils.Date("now")
    assert d.date == date.today()
    d = utils.Date("today")
    assert d.date == date.today()


def test_date_from_date_instance():
    d = utils.Date(utils.Date("2020-01-02"))
    assert d.date == date(2020, 1, 2)


def test_date_unsupported_type_raises():
    with pytest.raises(ValueError, match="Unsupported date type: int"):
        utils.Date(20200101)  # type: ignore[arg-type]


def test_date_format_and_str():
    d = utils.Date("2020-01-02")
    assert d.format("%d/%m/%Y") == "02/01/2020"
    assert str(d) == repr(d) == "2020-01-02"


def test_date_comparisons():
    a, b = utils.Date("2020-01-01"), utils.Date("2020-01-02")
    assert a < b and a <= b and b > a and b >= a
    assert a == utils.Date(date(2020, 1, 1))
    assert a != b
    assert (a == "2020-01-01") is False  # not a Date: NotImplemented -> False
