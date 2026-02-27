Moedas
======

O pacote tem 2 APIs que dão acesso a informações de moedas.


- :ref:`API OData de Moedas` com cotações de taxas de câmbio
- Webscraping no :ref:`Conversor de Moedas`

API OData de Moedas
-------------------


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

É importante notar que as datas estão no formato mês/dia/ano e os números não
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

Obtendo o CSV bruto
^^^^^^^^^^^^^^^^^^^

Para pipelines de dados onde o dado bruto deve ser persistido antes de qualquer transformação,
o parâmetro ``output='text'`` pode ser passado à função :py:func:`bcb.currency.get`.

Para um único símbolo é retornada uma ``str`` com o CSV bruto; para múltiplos símbolos é
retornado um ``dict`` mapeando símbolo ISO → CSV string.

.. code:: python

    from bcb import currency

    # único símbolo → str (CSV)
    raw = currency.get('USD', start='2024-01-01', end='2024-01-31', output='text')

    # múltiplos símbolos → dict[str, str]
    raws = currency.get(['USD', 'EUR'], start='2024-01-01', end='2024-01-31', output='text')
    # raws['USD'] → CSV string
    # raws['EUR'] → CSV string

    # salvar em disco
    with open('usd_raw.csv', 'w') as f:
        f.write(raw)

O CSV retornado usa ponto-e-vírgula como separador, datas no formato ``DDMMYYYY`` e vírgula
como separador decimal — exatamente como devolvido pela API PTAX do BCB.
O comportamento padrão (retorno de DataFrame) é mantido quando o parâmetro não é informado.

