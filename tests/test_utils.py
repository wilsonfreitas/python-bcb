from datetime import datetime, date

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
    d = utils.Date(None)
    assert d.date == date(1900, 1, 1)
    d = utils.Date("now")
    assert d.date == date.today()
    d = utils.Date("today")
    assert d.date == date.today()
