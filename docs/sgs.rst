SGS
###

O módulo ``sgs`` obtem os dados do webservice do Banco Central,
interface json do serviço BCData/SGS - 
`Sistema Gerenciador de Séries Temporais (SGS) <https://www3.bcb.gov.br/sgspub/localizarseries/localizarSeries.do?method=prepararTelaLocalizarSeries>`_.


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
    plt.legend().set_visible(False)

.. plot:: plots/sgs1.py
