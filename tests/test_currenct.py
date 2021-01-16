
from bcb import currency


def test_currency_id():
    assert currency.get_currency_id('USD') == 61
