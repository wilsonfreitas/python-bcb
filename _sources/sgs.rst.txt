SGS
===

A função :py:func:`bcb.sgs.get` obtém os dados do webservice do Banco Central,
interface JSON do serviço BCData/SGS -
`Sistema Gerenciador de Séries Temporais (SGS) <https://www3.bcb.gov.br/sgspub/localizarseries/localizarSeries.do?method=prepararTelaLocalizarSeries>`_.

Os parâmetros ``start`` e ``end`` aceitam strings ``YYYY-MM-DD``, ``datetime.date``, ``datetime.datetime`` ou :py:class:`bcb.utils.Date`. Também é possível usar ``last`` para buscar os últimos ``n`` pontos disponíveis.

Timeout em consultas longas
---------------------------

Por padrão, as requisições usam o timeout global do cliente HTTP compartilhado.
Para consultas SGS com janelas grandes ou respostas lentas, informe ``timeout``
na chamada. O valor é aplicado por tentativa HTTP; quando houver retry, cada
tentativa usa o mesmo timeout.

.. code:: python

    from bcb import sgs

    df = sgs.get(11, start="1990-01-01", end="2026-01-01", timeout=120)
    raw = sgs.get_json(11, start="1990-01-01", timeout=120)

Se a consulta continuar lenta mesmo com timeout maior, divida o período em
janelas menores e concatene os resultados.


Formato tidy no SGS
-------------------

Por padrão, :py:func:`bcb.sgs.get` retorna um DataFrame no formato largo. Para
retornar uma tabela longa, use ``tidy=True``. Nesse modo, o DataFrame tem as
colunas ``Date``, ``series`` e ``value``. A coluna ``series`` usa o nome
informado em ``codes``; quando nenhum nome é informado, usa o código numérico
da série.

.. ipython:: python

    from bcb import sgs
    sgs.get({'SELIC': 11, 'IPCA': 433}, start='2024-01-01', tidy=True).head()

O parâmetro ``tidy`` só afeta o retorno ``output='dataframe'``. Quando
``output='text'`` é usado, a função continua retornando o JSON bruto.


Exemplos
--------

.. ipython:: python

    from bcb import sgs
    import matplotlib.pyplot as plt
    import matplotlib as mpl
    mpl.style.use('bmh')

    df = sgs.get({'IPCA': 433}, start='2002-02-01')
    df.index = df.index.to_period('M')
    df.head()

.. ipython:: python

    dfr = df.rolling(12)
    i12 = dfr.apply(lambda x: (1 + x/100).prod() - 1).dropna() * 100
    i12.head()

.. ipython:: python

    i12.plot(figsize=(12,6))
    plt.title('Fonte: https://dadosabertos.bcb.gov.br', fontsize=10)
    plt.suptitle('IPCA acumulado 12 meses - Janela Móvel', fontsize=18)
    plt.xlabel('Data')
    plt.ylabel('%')
    @savefig sgs1.png
    plt.legend().set_visible(False)


Obtendo o JSON bruto
--------------------

A função :py:func:`bcb.sgs.get_json` retorna o JSON bruto da API para um único código.
Para pipelines de dados onde o dado bruto deve ser persistido antes de qualquer transformação,
o parâmetro ``output='text'`` pode ser passado à função :py:func:`bcb.sgs.get`.

Para um único código é retornada uma ``str``; para múltiplos códigos é retornado um ``dict``
mapeando código inteiro → JSON string.

.. code:: python

    from bcb import sgs

    # único código → str
    raw = sgs.get(433, start='2024-01-01', output='text')

    # múltiplos códigos → dict[int, str]
    raws = sgs.get([433, 189], start='2024-01-01', output='text')
    # raws[433] → JSON string do IPCA
    # raws[189] → JSON string do IGP-M

    # salvar em disco
    with open('ipca_raw.json', 'w') as f:
        f.write(raw)

O JSON retornado é um array de objetos com os campos ``data`` e ``valor``, exatamente como
devolvido pela API BCData/SGS.
O comportamento padrão (retorno de DataFrame) é mantido quando o parâmetro não é informado.


Dados de Inadimplência de Operações de Crédito
==============================================

Os modos aceitos são ``PF`` (pessoas físicas), ``PJ`` (pessoas jurídicas) e ``total``; ``all`` é aceito como alias de ``total``. Os locais devem ser todos estados ou todos regiões, sem misturar os dois tipos na mesma chamada.

.. ipython:: python

    from bcb.sgs.regional_economy import get_non_performing_loans
    from bcb.utils import BRAZILIAN_REGIONS, BRAZILIAN_STATES
    import pandas as pd
    get_non_performing_loans(["RR"], last=10, mode="all")

.. ipython:: python

    northeast_states = BRAZILIAN_REGIONS["NE"]
    get_non_performing_loans(northeast_states, last=5, mode="pj")

.. ipython:: python

    get_non_performing_loans(BRAZILIAN_STATES, mode="PF", start="2024-01-01")