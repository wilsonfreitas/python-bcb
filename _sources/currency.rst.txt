Moedas
======

O pacote tem 2 APIs que dão acesso a informações de moedas.


- :ref:`API OData` com cotações de taxas de câmbio
- Webscraping no :ref:`Conversor de Moedas`

API OData
---------


.. _documentacao: https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/documentacao

__ documentacao_

A classe :py:class:`bcb.PTAX` retorna cotações de moedas os obtidas a partir da `API de Moedas`__ do BCB.
Esta implementação é mais estável que a do :ref:`Conversor de Moedas`.

.. ipython:: python

    from bcb import PTAX
    ptax = PTAX()
    ptax.describe()


.. ipython:: python

    ptax.describe('Moedas')

    ep = ptax.get_endpoint('Moedas')
    ep.query().limit(10).collect()

.. ipython:: python

    ptax.describe('CotacaoMoedaDia')

    ep = ptax.get_endpoint('CotacaoMoedaDia')
    (ep.query()
       .parameters(moeda='AUD', dataCotacao='1/31/2022')
       .collect())

É importante notar que as datas estão no formato dia/mês/ano e os números não
são preenchidos com 0 para ter 2 dígitos.

.. ipython:: python

    ptax.describe('CotacaoMoedaPeriodo')
    
    ep = ptax.get_endpoint('CotacaoMoedaPeriodo')
    (ep.query()
       .parameters(moeda='AUD',
                   dataInicial='1/1/2022',
                   dataFinalCotacao='1/5/2022')
       .collect())

Conversor de Moedas
-------------------

O módulo :py:mod:`bcb.currency` obtem dados de moedas do conversor de moedas do Banco Central através de webscraping.

.. ipython:: python

    from bcb import currency
    df = currency.get(['USD', 'EUR'],
                      start='2000-01-01',
                      end='2021-01-01',
                      side='ask')
    df.head()

    @savefig currency1.png
    df.plot(figsize=(12, 6));


.. ipython:: python

    currency.get_currency_list().head()

