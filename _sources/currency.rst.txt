Moedas
######

O pacote tem 2 APIs que dão acesso a informações de moedas.


- Webscraping no :ref:`Conversor de Moedas`
- :ref:`API OData` com cotações de taxas de câmbio


Conversor de Moedas
-------------------

O módulo ``currency`` obtem dados de moedas do conversor de moedas do Banco Central através de webscraping.

.. currentmodule:: bcb.currency


.. autofunction:: get


.. ipython:: python

    from bcb import currency
    df = currency.get(['USD', 'EUR'], start='2000-01-01', end='2021-01-01', side='ask')
    df.head()

.. ipython:: python

    df.plot(figsize=(12, 6));

.. plot:: plots/currency1.py


.. autofunction:: get_currency_list


.. ipython:: python

    currency.get_currency_list().head()

API OData
---------


.. _documentacao: https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/documentacao

__ documentacao_

Diferente da interface _`currency`, os dados são obtidos a partir da `API de Moedas`__.

.. currentmodule:: bcb


.. autoclass:: PTAX


.. ipython:: python

    from bcb import PTAX
    ptax = PTAX()
    ptax.describe()


.. ipython:: python

    ptax.describe('Moedas')

.. ipython:: python

    ptax.describe('CotacaoMoedaPeriodoFechamento')

.. ipython:: python

    ptax.describe('CotacaoMoedaPeriodo')
