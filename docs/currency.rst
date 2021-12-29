Moedas
######

O módulo ``currency`` obtem dados de moedas do conversor de moedas do Banco Central através de webscraping.

.. autofunction:: bcb.currency.get


.. ipython:: python

    from bcb import currency
    df = currency.get(['USD', 'EUR'], start='2000-01-01', end='2021-01-01', side='ask')
    df.head()

.. ipython:: python

    df.plot(figsize=(12, 6));

.. plot:: plots/currency1.py


.. autofunction:: bcb.currency.get_currency_list


.. ipython:: python

    currency.get_currency_list().head()

