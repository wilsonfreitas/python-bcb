IFData
######

A API IFData do Banco Central do Brasil pode ser acessada pela classe
:py:class:`bcb.IFDATA`.

.. _ifdata-dataset: https://dadosabertos.bcb.gov.br/dataset/ifdata---dados-selecionados-de-instituies-financeiras
.. _ifdata-web: https://www3.bcb.gov.br/ifdata/
.. _ifdata-odata: https://olinda.bcb.gov.br/olinda/servico/IFDATA/versao/v1/odata/
.. _ifdata-metodologia: https://www.bcb.gov.br/conteudo/dadosabertos/BCBDesig/IFData%20-%20Esclarecimentos%20e%20Metodologia.pdf

__ ifdata-dataset_

Os dados são obtidos a partir do conjunto `IFData - Dados selecionados
de instituições financeiras`__ do portal de dados abertos do BCB. A
documentação oficial informa que o IFData divulga, em formato aberto,
relatórios trimestrais de instituições autorizadas a funcionar e em
operação normal. As bases de origem citadas pelo BCB são o SCR
(``Sistema de Informações de Créditos``) e o Cosif
(``Plano Contábil das Instituições do Sistema Financeiro Nacional``).

Segundo a metodologia do IFData, os relatórios trimestrais são
disponibilizados 60 dias após as datas-bases de março, junho e setembro,
e 90 dias após a data-base de dezembro. O portal informa início em
março de 2000 e periodicidade trimestral.

Primeiro acesso
===============

O serviço IFData é uma API OData com três ``FunctionImports``. O método
``describe`` mostra os nomes dos endpoints, parâmetros e colunas.

Os blocos ``ipython`` desta página são executados no build da
documentação. Blocos ``code`` são exemplos para copiar e
adaptar, mas não são executados durante o build.

.. ipython:: python

    from bcb import IFDATA

    ifdata = IFDATA(timeout=120)
    ifdata.describe(full=False)

Os endpoints disponíveis são:

``ListaDeRelatorio``
   Lista os relatórios existentes no serviço. Retorna ``NomeRelatorio``
   e ``NumeroRelatorio``.
``IfDataCadastro``
   Retorna o cadastro de instituições e conglomerados para uma data-base.
   Recebe o parâmetro ``AnoMes``.
``IfDataValores``
   Retorna os valores de um relatório em formato longo. Recebe os
   parâmetros ``AnoMes``, ``TipoInstituicao`` e ``Relatorio``.

Listando relatórios
===================

O primeiro passo prático é obter o catálogo de relatórios e usar a coluna
``NumeroRelatorio`` como parâmetro ``Relatorio`` em ``IfDataValores``.
Apesar de o parâmetro se chamar ``Relatorio``, o valor esperado é o
número retornado em ``NumeroRelatorio`` como string.

.. ipython:: python

    relatorios = (
        ifdata.get_endpoint("ListaDeRelatorio")
        .query()
        .collect()
    )

    relatorios[["NumeroRelatorio", "NomeRelatorio"]]

Na versão atual do serviço, alguns relatórios relevantes são:

* ``"1"``: Resumo
* ``"7"``: Carteira de Crédito Ativa - Por indexador
* ``"8"``: Carteira de crédito ativa - por nível de risco da operação
* ``"9"``: Carteira de crédito ativa - por região geográfica
* ``"10"``: Carteira de crédito ativa - quantidade de clientes e de operações
* ``"11"``: Carteira de crédito ativa Pessoa Física - modalidade e prazo de vencimento
* ``"12"``: Carteira de crédito ativa Pessoa Jurídica - por atividade econômica (CNAE)
* ``"13"``: Carteira de crédito ativa Pessoa Jurídica - modalidade e prazo de vencimento
* ``"14"``: Carteira de crédito ativa Pessoa Jurídica - por porte do tomador

Use sempre ``ListaDeRelatorio`` quando for construir uma análise nova,
pois a disponibilidade de relatórios pode mudar ao longo do tempo.

Parâmetros principais
=====================

``AnoMes``
   Data-base no formato ``AAAAMM``, por exemplo ``202403`` para março
   de 2024. O IFData é trimestral; na prática, use meses ``03``, ``06``,
   ``09`` e ``12``.
``TipoInstituicao``
   Nível de consolidação usado no relatório. No endpoint OData, os
   códigos práticos são:

   * ``1``: Conglomerados Prudenciais e Instituições Independentes.
   * ``2``: Conglomerados Financeiros e Instituições Independentes.
   * ``3``: Instituições Individuais.

   A interface web do IFData usa ids internos diferentes nos seus
   arquivos, como ``1009``, ``1005`` e ``1006``. Esses ids não são os
   códigos esperados por ``IfDataValores`` no ``python-bcb``.
``Relatorio``
   Código do relatório, como string, retornado por ``ListaDeRelatorio``.
   Exemplo: ``"1"`` para ``Resumo`` e ``"11"`` para o relatório de
   carteira de crédito ativa de pessoa física por modalidade e prazo.

Consultando cadastro
====================

O cadastro ajuda a interpretar ``CodInst`` e a distinguir instituições
individuais de conglomerados. A coluna ``Data`` é convertida para
``datetime64`` pelo ``python-bcb``.

.. ipython:: python

    cadastro_ep = ifdata.get_endpoint("IfDataCadastro")

    cadastro = (
        cadastro_ep.query()
        .parameters(AnoMes=202403)
        .limit(10)
        .collect()
    )

    cadastro[
        [
            "Data",
            "CodInst",
            "NomeInstituicao",
            "Td",
            "CodConglomeradoFinanceiro",
            "CodConglomeradoPrudencial",
        ]
    ]

Na versão atual do pacote, se você usar ``select`` em ``IfDataCadastro``,
mantenha a coluna ``Data`` na seleção. A conversão automática de datas
desse endpoint espera essa coluna no resultado.

Consultando valores
===================

``IfDataValores`` retorna os dados em formato longo: cada linha identifica
instituição, relatório, conta/coluna e valor em ``Saldo``. Para montar uma
tabela analítica, normalmente é necessário filtrar ``NomeColuna`` ou
``Conta`` e depois fazer ``pivot`` ou ``merge`` com o cadastro.

O exemplo abaixo obtém a métrica ``Carteira de Crédito Classificada`` do
relatório ``Resumo`` para conglomerados prudenciais e instituições
independentes na data-base de março de 2024.

.. ipython:: python

    valores_ep = ifdata.get_endpoint("IfDataValores")

    credito_resumo = (
        valores_ep.query()
        .parameters(AnoMes=202403, TipoInstituicao=1, Relatorio="1")
        .filter(valores_ep.NomeColuna == "Carteira de Crédito Classificada")
        .orderby(valores_ep.Saldo.desc())
        .limit(10)
        .collect()
    )

    cadastro_completo = cadastro_ep.query().parameters(AnoMes=202403).collect(timeout=120)

    credito_resumo = credito_resumo.merge(
        cadastro_completo[["CodInst", "NomeInstituicao"]],
        on="CodInst",
        how="left",
    )

    credito_resumo[["NomeInstituicao", "AnoMes", "NomeColuna", "Saldo"]]

Diferenças entre datasets
=========================

O resultado de ``IfDataValores`` muda conforme a combinação de
``AnoMes``, ``TipoInstituicao`` e ``Relatorio``. A lista de relatórios é
um catálogo geral; ela não garante que toda combinação de tipo de
instituição e data-base terá dados.

Por exemplo, para ``AnoMes=202403`` a chamada abaixo retornava dados para
``TipoInstituicao=2`` no relatório ``"11"``, mas retornava ``DataFrame``
vazio para ``TipoInstituicao=1`` e ``TipoInstituicao=3``. Isso não indica
necessariamente erro de rede; normalmente indica que aquela combinação de
parâmetros não existe no conjunto divulgado.

.. ipython:: python

    pf_tipo_2 = (
        valores_ep.query()
        .parameters(AnoMes=202403, TipoInstituicao=2, Relatorio="11")
        .filter(valores_ep.NomeColuna == "Total da Carteira de Pessoa Física")
        .limit(10)
        .collect()
        .merge(
            cadastro_completo[["CodInst", "NomeInstituicao"]],
            on="CodInst",
            how="left",
        )
    )

    pf_tipo_2[
        ["TipoInstituicao", "NomeInstituicao", "NomeRelatorio", "NomeColuna", "Saldo"]
    ]

Ao explorar um relatório novo, comece com ``limit`` e filtros seletivos.
Depois verifique ``NomeRelatorio``, ``NumeroRelatorio``, ``NomeColuna``
e ``DescricaoColuna`` antes de agregar valores.

Comparando instituições com dados de crédito
============================================

O exemplo abaixo compara as maiores carteiras de crédito classificadas
entre instituições individuais em março de 2024. Usamos
``TipoInstituicao=3`` para evitar misturar CNPJs individuais com
conglomerados.

.. ipython:: python

    import pandas as pd

    ANO_MES = 202403
    TIPO_INSTITUICAO = 3
    RELATORIO_RESUMO = "1"

    valores_ep = ifdata.get_endpoint("IfDataValores")
    cadastro_ep = ifdata.get_endpoint("IfDataCadastro")

    credito = (
        valores_ep.query()
        .parameters(
            AnoMes=ANO_MES,
            TipoInstituicao=TIPO_INSTITUICAO,
            Relatorio=RELATORIO_RESUMO,
        )
        .filter(valores_ep.NomeColuna == "Carteira de Crédito Classificada")
        .orderby(valores_ep.Saldo.desc())
        .limit(10)
        .collect()
    )

    comparativo = (
        credito.merge(
            cadastro_completo[["CodInst", "NomeInstituicao", "Tcb", "Td", "Sr"]],
            on="CodInst",
            how="left",
        )
        .assign(
            Saldo_bilhoes=lambda df: df["Saldo"] / 1e9,
            Participacao_top10=lambda df: df["Saldo"] / df["Saldo"].sum(),
        )
        [
            [
                "NomeInstituicao",
                "Saldo_bilhoes",
                "Participacao_top10",
                "Tcb",
                "Td",
                "Sr",
            ]
        ]
    )

    comparativo

.. ipython:: python

    @savefig ifdata_credito_comparativo.png
    ax = comparativo.sort_values("Saldo_bilhoes").plot.barh(x="NomeInstituicao", y="Saldo_bilhoes", legend=False, figsize=(13, 7), xlabel="Saldo / 1e9", ylabel="", title="Carteira de crédito classificada - instituições individuais")
    ax.figure.subplots_adjust(left=0.42)
    ax;

O campo ``Saldo`` é o valor numérico retornado pela API. A unidade e a
forma de apresentação podem variar por relatório; antes de publicar
valores monetários, confira ``DescricaoColuna`` e a composição/nota do
relatório na `interface IF.data <https://www3.bcb.gov.br/ifdata/>`_.

Evolução temporal
=================

Para analisar evolução temporal, consulte poucas datas-bases e mantenha o
mesmo ``TipoInstituicao`` e o mesmo ``NomeColuna`` ao longo da série. O
exemplo abaixo acompanha cinco instituições individuais em cinco
trimestres.

.. ipython:: python

    import pandas as pd

    from bcb import IFDATA

    ifdata = IFDATA(timeout=120)
    valores_ep = ifdata.get_endpoint("IfDataValores")
    cadastro_ep = ifdata.get_endpoint("IfDataCadastro")

    filtro_codigos = ((valores_ep.CodInst == "00360305") | (valores_ep.CodInst == "00000000") | (valores_ep.CodInst == "60701190") | (valores_ep.CodInst == "60746948") | (valores_ep.CodInst == "90400888"))

    credito_202303 = valores_ep.query().parameters(AnoMes=202303, TipoInstituicao=3, Relatorio="1").filter(valores_ep.NomeColuna == "Carteira de Crédito Classificada", filtro_codigos).collect().assign(AnoMes=202303)
    credito_202306 = valores_ep.query().parameters(AnoMes=202306, TipoInstituicao=3, Relatorio="1").filter(valores_ep.NomeColuna == "Carteira de Crédito Classificada", filtro_codigos).collect().assign(AnoMes=202306)
    credito_202309 = valores_ep.query().parameters(AnoMes=202309, TipoInstituicao=3, Relatorio="1").filter(valores_ep.NomeColuna == "Carteira de Crédito Classificada", filtro_codigos).collect().assign(AnoMes=202309)
    credito_202312 = valores_ep.query().parameters(AnoMes=202312, TipoInstituicao=3, Relatorio="1").filter(valores_ep.NomeColuna == "Carteira de Crédito Classificada", filtro_codigos).collect().assign(AnoMes=202312)
    credito_202403 = valores_ep.query().parameters(AnoMes=202403, TipoInstituicao=3, Relatorio="1").filter(valores_ep.NomeColuna == "Carteira de Crédito Classificada", filtro_codigos).collect().assign(AnoMes=202403)

    historico = pd.concat([credito_202303, credito_202306, credito_202309, credito_202312, credito_202403], ignore_index=True)
    cadastro_202403 = cadastro_completo
    historico = historico.merge(cadastro_202403[["CodInst", "NomeInstituicao"]], on="CodInst", how="left")
    tabela = historico.pivot_table(index="AnoMes", columns="NomeInstituicao", values="Saldo", aggfunc="first")
    tabela_bilhoes = tabela / 1e9
    tabela_bilhoes.index = pd.to_datetime(tabela_bilhoes.index.astype(str), format="%Y%m").strftime("%Y-%m")

    tabela_bilhoes

.. ipython:: python

    @savefig ifdata_credito_evolucao.png
    ax = tabela_bilhoes.plot(figsize=(13, 6), marker="o", xlabel="Data-base", ylabel="Saldo / 1e9", title="Evolução da carteira de crédito classificada")
    ax.legend(loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=8)
    ax.figure.subplots_adjust(right=0.62)
    ax;

Cuidados de interpretação
=========================

* Não some resultados de ``TipoInstituicao`` diferentes. Eles representam
  níveis de consolidação distintos e podem conter sobreposição.
* ``CodInst`` muda de significado conforme o nível de consolidação. Em
  conglomerados, códigos como ``C008...`` representam entidades
  consolidadas; em instituições individuais, os códigos são de instituições
  separadas por personalidade jurídica.
* Instituições individuais são apresentadas em nível não consolidado. A
  metodologia do BCB informa que participações societárias e agências no
  exterior são registradas como investimento nesse formato.
* Conglomerados financeiros consolidam entidades financeiras vinculadas.
  Conglomerados prudenciais são mais amplos e podem incluir, conforme a
  metodologia, administradoras de consórcio, instituições de pagamento e
  outras entidades relevantes para risco prudencial.
* Um ``DataFrame`` vazio pode significar combinação inexistente de
  ``AnoMes``, ``TipoInstituicao`` e ``Relatorio``. Confirme trocando um
  parâmetro por vez e consultando primeiro ``ListaDeRelatorio``.
* As notas dos relatórios do IFData podem trazer regras específicas como
  ``NI`` para informações não prestadas até a publicação, ``NA`` para não
  aplicável e republicação de informações quando há reapresentação.
* O BCB informa que não há informações sobre administradores de consórcios
  na metodologia geral do IFData.
* Consultas amplas podem ser lentas. Prefira filtros, ``limit`` e poucos
  períodos por chamada quando estiver explorando em notebook.

Fontes oficiais
===============

* `Conjunto IFData no portal de dados abertos <https://dadosabertos.bcb.gov.br/dataset/ifdata---dados-selecionados-de-instituies-financeiras>`_
* `Interface web IF.data <https://www3.bcb.gov.br/ifdata/>`_
* `Endpoint OData IFData <https://olinda.bcb.gov.br/olinda/servico/IFDATA/versao/v1/odata/>`_
* `Esclarecimentos e Metodologia do IFData <https://www.bcb.gov.br/conteudo/dadosabertos/BCBDesig/IFData%20-%20Esclarecimentos%20e%20Metodologia.pdf>`_
