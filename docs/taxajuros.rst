Taxas de Juros
##############

A API de taxas de juros de operações de crédito pode ser acessada através da
classe :py:class:`bcb.TaxaJuros`.

.. _documentacao: https://olinda.bcb.gov.br/olinda/servico/TaxaJuros/versao/v1/documentacao

__ documentacao_

Os dados são obtidos a partir da `API de Taxas de Juros`__.


Esta API tem os ``EntitySets``:

.. ipython:: python

    from bcb import TaxaJuros
    em = TaxaJuros()
    em.describe()

As características do ``EntitySets`` podem ser visualizadas por:

.. ipython:: python

    em.describe("TaxasJurosDiariaPorInicioPeriodo")

Vejamos um gráfico da mediana das taxas de juros do cheque especial praticada
pelas instituições financeiras.

.. ipython:: python

    import pandas as pd

    ep = em.get_endpoint('TaxasJurosDiariaPorInicioPeriodo')
    df_cheque = (ep.query()
                   .filter(ep.Segmento == 'PESSOA FÍSICA',
                           ep.Modalidade == 'Cheque especial - Prefixado')
                   .collect())
    grp = df_cheque.groupby('InicioPeriodo')
    df_mean = grp.agg({'TaxaJurosAoMes': 'median'})

    @savefig taxajuros1.png
    df_mean['TaxaJurosAoMes'].plot(figsize=(16,6), style='o', markersize=1,
                                   xlabel='Data', ylabel='Taxa',
                                   title='Mediana das Taxas de Juros de Cheque Especial - Fonte:BCB');

