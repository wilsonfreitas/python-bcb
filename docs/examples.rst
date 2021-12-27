
Exemplos
========

.. ipython:: python

    import pandas as pd
    from bcb import currency

    df = currency.get(['USD', 'EUR', 'GBP', 'CHF', 'CAD'], start='2000-01-01', end='2021-01-01')
    df