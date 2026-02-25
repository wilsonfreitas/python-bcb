
OData
=====

Diversas APIs disponíveis no `portal de dados abertos <https://dadosabertos.bcb.gov.br/>`_ do Banco Central
implementam o protocolo `OData <https://www.odata.org/>`_, são centenas de APIs.

O ``python-bcb`` tem algumas classes que implementam APIs OData:

- :py:class:`bcb.odata.api.Expectativas`: Expectativas de mercado para os indicadores macroeconômicos da Pesquisa Focus
- :py:class:`bcb.odata.api.PTAX`: Dólar comercial
- :py:class:`bcb.odata.api.TaxaJuros`: Taxas de juros de operações de crédito por instituição financeira
- :py:class:`bcb.odata.api.IFDATA`: Dados selecionados de instituições financeiras
- :py:class:`bcb.odata.api.MercadoImobiliario`: Informações do Mercado Imobiliário
- :py:class:`bcb.odata.api.SPI`: Estatísticas do SPI (Sistema de Pagamentos Instantâneos)
- Veja todas as APIs implementadas em :ref:`APIs OData`.

Estas APIs foram implementadas em classes por serem as mais populares, entretanto,
qualquer API OData pode ser acessada através da classe :py:class:`bcb.odata.api.ODataAPI` que abstrai o acesso
a API a partir da URL da API que está disponível no `portal de dados abertos <https://dadosabertos.bcb.gov.br/>`_
do Banco Central.
Veja mais detalhes em :ref:`Classe ODataAPI`.

Segue um exemplo de como acessar a API do PIX.

.. ipython:: python

    from bcb import SPI
    pix = SPI()

É necessário importar e criar um objeto da classe que implementa a API, neste caso a classe ``SPI``.
Tendo o objeto, executar o método ``describe`` para visualizar o *endpoints* disponíveis na API.


.. ipython:: python

    pix.describe()

Como vemos, a API do PIX tem 4 *endpoints* (``EntitySets``).
Para ver as informações retornadas por cada *endpoint* é só executar o método ``describe`` passando como argumento
o nome do *endpoint*.

.. ipython:: python

    pix.describe("PixLiquidadosAtual")

Vemos que o *endpoint* ``PixLiquidadosAtual`` retorna 4 propriedades:

- ``Data<datetime>``: data das operações
- ``Quantidade<int>``: quantidade de operações realizadas na data
- ``Total<float>``: financeiro das operações realizdas na data
- ``Media<float>``: média das operações realizadas na data

As propriedades são atributos de objetos da classe :py:class:`bcb.odata.api.Endpoint`, retornados pelo método
``get_endpoint``.

.. ipython:: python

    ep = pix.get_endpoint("PixLiquidadosAtual")
    ep.Data
    ep.Media

Para acessar os dados deste *endpoint* é necessário executar uma ``query`` nesse objeto.

.. ipython:: python

    ep.query().limit(5).collect()

Ao realizar a ``query`` no *endpoint* limitamos a consulta a retornar 10 elementos, apenas para visualizar os dados
da consulta.
A consulta retorna um DataFrame pandas onde as colunas são as propriedades do *endpoint*.

Veremos abaixo, com mais detalhes, como realizar consultas nas APIs e quais os tipos de *endpoints* disponíveis
(``EntitySets`` e ``FunctionImports``).

Como Realizar Consultas em APIs OData
-------------------------------------

As consultas são realizadas através do método ``query`` da classe :py:class:`bcb.odata.api.Endpoint`.
Este método retorna um objeto :py:class:`bcb.odata.framework.ODataQuery` que abstrai a consulta e permite executar
algumas firulas como: filtros e ordenação.
A classe :py:class:`bcb.odata.framework.ODataQuery` tem os seguintes métodos:

- :py:meth:`bcb.odata.framework.ODataQuery.filter`: define filtros na consulta, com uma clausula ``where`` no SQL.
- :py:meth:`bcb.odata.framework.ODataQuery.select`: seleciona as propriedades retornadas pela consulta.
- :py:meth:`bcb.odata.framework.ODataQuery.orderby`: ordena a consulta pelas propriedades.
- :py:meth:`bcb.odata.framework.ODataQuery.limit`: limita os resultados a ``n`` registros.
- :py:meth:`bcb.odata.framework.ODataQuery.parameters`: *endpoints* do tipo ``FunctionImports`` possuem parâmetros que são definidos por este método.
- :py:meth:`bcb.odata.framework.ODataQuery.collect`: o *framework* tem uma abordagem *lazy*, dessa forma, este método realiza a consulta trazendo os dados e retornando um DataFrame.
- :py:meth:`bcb.odata.framework.ODataQuery.text`: este método retorna o texto (formato json) retornado pela API.
- :py:meth:`bcb.odata.framework.ODataQuery.show`: imprime a estrutura da consulta.

Os métodos ``filter``, ``select``, ``orderby``, ``limit`` e ``parameters`` retornam o objeto
:py:class:`bcb.odata.framework.ODataQuery`, e isso permite a realização de chamadas aninhadas que compõem a consulta.

Por exemplo, na consulta do PIX, as datas não estão ordenadas, temos dias de 2021, 2022 e 2023 nos 10 registros
retornados.
Vamos ordernar pela propriedade ``Data`` de forma decrescente.

.. ipython:: python

    ep.query().orderby(ep.Data.desc()).limit(5).collect()

Veja que a consulta retorna as datas mais recentes primeiro.

Gosto de estruturar as consultas como uma *query* SQL.
Sigamos com um exemplo:

.. code:: SQL

    select Data, Media
    from PIX
    where Data >= "2023-01-01"
    order by Media desc
    limit 10

Quero obter os 10 dias em 2023 que apresentam as maiores médias transacionadas no PIX.

Para executar essa query utilizo o método ``select`` passando as propriedades Data e Media,
encadeio o método ``filter`` filtrando a propriedade Data maiores que 2023-01-01, e note
que aqui utilizo um objeto ``datetime``, pois na descrição do *endpoint* ``PixLiquidadosAtual``
a propriedade Data é do tipo ``datetime``.
Sigo com o método ``orderby`` passando a propriedade média e indicando que a ordenação é decrescente e concluo com
o método ``limit`` para obter os 10 primeiros registros.
Na última linha executo o método ``collect`` que executa a consulta e retorna um DataFrame com os resultados.

.. ipython:: python

    from datetime import datetime
    (ep.query()
        .select(ep.Data, ep.Media)
        .filter(ep.Data >= datetime(2023, 1, 1))
        .orderby(ep.Media.desc())
        .limit(5)
        .collect())

Visualizando a Consulta
^^^^^^^^^^^^^^^^^^^^^^^

Algumas consultas podem ficar bastante complicadas, dependendo da quantidade de elementos que compõem a consulta.
Para ajudar na construção e na depuração da *query*, criamos o método ``show`` imprime a query na tela,
mas não a executa.

.. ipython:: python

    (ep.query()
        .select(ep.Data, ep.Media)
        .filter(ep.Data >= datetime(2023, 1, 1))
        .orderby(ep.Media.desc())
        .limit(5)
        .show())


Filtrando Dados
^^^^^^^^^^^^^^^

Os filtros são criados com o método ``filter`` e aplicados às propriedades do *endpoint*, por isso é necessário
conhecê-lo, o que deve ser feito com o método ``describe``.

.. ipython:: python

    from bcb import Expectativas
    em = Expectativas()
    em.describe('ExpectativasMercadoTop5Anuais')

O *endpoint* ``ExpectativasMercadoTop5Anuais`` da API de Expectativas possui a propriedade ``Indicador``, do tipo
``str``.
Vamos filtrar os dados com a propriedade ``Indicador`` igual a ``IPCA``.
Como o tipo dessa propriedade é ``str``, utilizamos uma string no filtro e o operador ``==``, que representa igualdade.

.. ipython:: python

    ep = em.get_endpoint('ExpectativasMercadoTop5Anuais')
    query = ep.query().filter(ep.Indicador == 'IPCA').limit(5)
    query.show()

O método ``show`` apresenta os parâmetros da *query* formatados, com isso podemos visualizar como os parâmetros da
consulta serão enviados à API.
Note que o operador ``==`` foi convertido para ``eq``.
Podemos utilizar todos os operadores de comparação nos filtros.

.. ipython:: python

    query.collect()

Mais filtros podem ser adicionados ao método ``filter``, e também podemos aninhar chamadas do método ``filter``.

.. ipython:: python

    query = (ep.query()
               .filter(ep.Indicador == 'IPCA', ep.DataReferencia == 2023)
               .filter(ep.Data >= '2022-01-01')
               .filter(ep.tipoCalculo == 'C')
               .limit(5))
    query.show()
    query.collect()

Todos os filtros estão no atributo ``$filter`` da consulta e são concatenados com o operador booleano ``and``.

É necessário conhecer o tipo da propriedade para saber como passar o objeto para a consulta.
Os tipos de propriedade podem ser: str, float, int e datetime.
Por exemplo, na API do PIX, a propriedade ``Data`` é do tipo ``datetime`` e por isso é necessário passar um
objeto ``datetime`` para o método ``filter``.

.. ipython:: python

    ep = pix.get_endpoint("PixLiquidadosAtual")
    (ep.query()
       .filter(ep.Data >= datetime(2023, 1, 1))
       .limit(5)
       .show())

O objeto ``datetime`` é formatado como data na consulta, note que não há aspas na definição da data no filtro.

Ordenando os Dados
^^^^^^^^^^^^^^^^^^

A ordenação é definida no método ``orderby`` passando um objeto da classe
:py:class:`bcb.odata.framework.ODataPropertyOrderBy` que é obtida dos métodos ``asc`` e ``desc`` da propriedade.

.. ipython:: python

    ep = pix.get_endpoint("PixLiquidadosAtual")
    ep.Data.asc()

Este objeto é passado para o método ``orderby`` na *tripa* na qual a *query* é construída.

.. ipython:: python

    query = (ep.query()
               .orderby(ep.Data.asc())
               .limit(5))
    query.show()
    query.collect()

O método ``orderby`` pode receber diversas propriedades para a definição da ordenação.

.. ipython:: python

    ep = em.get_endpoint('ExpectativasMercadoTop5Anuais')
    query = (ep.query()
               .orderby(ep.Data.desc(), ep.Indicador.desc())
               .limit(5))
    query.show()

Também podem ser realizadas chamadas aninhadas do método ``orderby``.

.. ipython:: python

    query = (ep.query()
               .orderby(ep.Data.desc())
               .orderby(ep.Indicador.desc())
               .limit(5))
    query.show()

Vejam que a consulta é exatamente a mesma.


Selecionando as Propriedades
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

O médoto ``select`` funciona de forma muito semelhante ao *select* de uma *query* SQL.

.. ipython:: python

    ep = em.get_endpoint('ExpectativasMercadoTop5Anuais')
    (ep.query()
       .select(ep.Indicador, ep.Data, ep.DataReferencia, ep.tipoCalculo, ep.Media)
       .orderby(ep.Data.desc())
       .limit(5)
       .collect())

Selecionar as colunas é importante para reduzir o volume de dados trafegado, pois a API do BCB não tem um bom
desempenho, logo, essas configurações aceleram as consultas.


Método ``limit``
^^^^^^^^^^^^^^^^

O método ``limit`` define a quantidade de linhas que será retornada pela consulta.
Esse método é importante para investigar as consultas na API de forma rápida.

.. ipython:: python

    ep = pix.get_endpoint("PixLiquidadosAtual")
    (ep.query()
       .filter(ep.Data >= datetime(2023, 1, 1))
       .limit(5)
       .collect())



Tipos de *endpoints*
^^^^^^^^^^^^^^^^^^^^

Como foi visto anteriormente, a API do PIX (``SPI``) possui 4 ``EntitySets`` e estes são os *endpoints* dessa API.
Entretanto, há APIs que têm um outro tipo de *endpoint*, os ``FunctionImports``.
A API do PTAX, por exemplo

.. ipython:: python

    from bcb import PTAX

    ptax = PTAX()
    ptax.describe()

Esta API tem 1 ``EntitySet`` e 6 ``FunctionImports``.
Assim como os ``EntitySets``, os ``FunctionImports`` também retornam dados em formato tabular.
A principal diferença entre os ``EntitySets`` e ``FunctionImports`` é que estes possuem parâmetros, como uma função, e
estes parâmetros devem ser definidos para que a consulta seja realizada.

Vamos ver o *endpoint* ``CotacaoMoedaPeriodo``

.. ipython:: python

    ptax.describe("CotacaoMoedaPeriodo")

Este *endpoint* tem 3 parâmetros:

- codigoMoeda <str>
- dataInicial <str>
- dataFinalCotacao <str>

Para conhecer como os parâmetros devem ser definidos é necessário ler a documentação da API.
Eventualmente a definição dos parâmetros não é óbvia.
Por exemplo, neste *endpoint*, os parâmetros ``dataInicial`` e ``dataFinalCotacao`` são formatados com
mês-dia-ano (formato americano), ao invés de ano-mês-dia (formato ISO), e como o tipo dos parâmetros é ``str``,
uma formatação incorreta não retorna um erro, apenas retorna um DataFrame vazio.

Vamos realizar uma consulta para obter as cotações de dólar americano entre 2022-01-01 e 2022-01-05.

.. ipython:: python

    ep = ptax.get_endpoint("CotacaoMoedaPeriodo")
    (ep.query()
       .parameters(moeda="USD",
                   dataInicial="1/1/2022",
                   dataFinalCotacao="1/5/2022")
       .collect())

Note que a primeira data é 2022-01-03, pois os primeiros dias do ano não são úteis.
Podemos aplicar filtros nessa consulta utilizando o método ``filter``, da mesma forma que realizamos na consulta ao
``EntitySet``.

.. ipython:: python

    (ep.query()
       .parameters(moeda="USD",
                   dataInicial="1/1/2022",
                   dataFinalCotacao="1/5/2022")
       .filter(ep.tipoBoletim == "Fechamento")
       .collect())

Obtendo o Texto da API
^^^^^^^^^^^^^^^^^^^^^^

Uma alternativa ao DataFrame retornado pela consulta, via o método ``collect``, é obter o texto, em formato JSON
(padrão) ou XML, retornado pela consulta.

O método ``collect`` faz o *parsing* do texto retornado na consulta e cria um DataFrame, o método ``text`` retorna
esse texto bruto.

Isso é útil para fazer o armazenamento de dados da API para a construção de bancos de dados ou *data lakes*.

Para obter o conteúdo bruto, basta executar o método ``text`` ao invés do ``collect``, ao fim da cadeia da consulta.

.. ipython:: python

    ep = em.get_endpoint('ExpectativasMercadoTop5Anuais')
    (ep.query()
       .select(ep.Indicador, ep.Data, ep.DataReferencia, ep.tipoCalculo, ep.Media)
       .orderby(ep.Data.desc())
       .limit(5)
       .text())

O texto retornado está no formato JSON.
Contudo, as APIs OData também retornam conteúdo em XML.
Para isso incluímos o método ``format`` na cadeia da consulta e passamos como parâmetro o tipo desejado.

.. ipython:: python

    ep = em.get_endpoint('ExpectativasMercadoTop5Anuais')
    (ep.query()
       .select(ep.Indicador, ep.Data, ep.DataReferencia, ep.tipoCalculo, ep.Media)
       .orderby(ep.Data.desc())
       .format("xml")
       .limit(5)
       .text())

O parâmetro ``output='text'``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Para pipelines de dados onde é necessário persistir o dado bruto antes de qualquer transformação
(camada SOR/SOT), o parâmetro ``output='text'`` pode ser passado diretamente ao método ``collect``
ou ao método ``get`` do endpoint.
Isso evita serializar um DataFrame de volta para texto, o que pode ser uma operação com perda de informação.

.. code:: python

    ep = em.get_endpoint('ExpectativasMercadoTop5Anuais')

    # via query chain
    raw = (ep.query()
              .filter(ep.Indicador == 'IPCA')
              .limit(100)
              .collect(output='text'))

    # via atalho get()
    raw = ep.get(ep.Indicador == 'IPCA', limit=100, output='text')

    # salvar em disco
    with open('expectativas_raw.json', 'w') as f:
        f.write(raw)

O texto retornado é o JSON bruto da resposta OData, incluindo o campo ``@odata.context`` e o array ``value``.
O comportamento padrão (retorno de DataFrame) é mantido quando o parâmetro não é informado.


Classe ODataAPI
---------------

O portal de Dados Abertos to Banco Central apresenta diversas APIs OData, são
dezenas de APIs disponíveis.
A URL com metadados de cada API pode ser obtida no `portal <https://dadosabertos.bcb.gov.br>`_.
A classe :py:class:`bcb.odata.api.ODataAPI` permite acessar qualquer API Odata de posse da sua URL.

Por exemplo, a API de estatísticas de operações registradas no Selic tem a seguinte URL::

    https://olinda.bcb.gov.br/olinda/servico/selic_operacoes/versao/v1/odata/

que pode ser obtida no portal de dados abertos no `link <https://dadosabertos.bcb.gov.br/dataset/estatisticas-selic-operacoes>`_.

Essa API pode ser diretamente acessada através da classe :py:class:`bcb.odata.api.ODataAPI`.

.. ipython:: python

    from bcb import ODataAPI
    url = "https://olinda.bcb.gov.br/olinda/servico/selic_operacoes/versao/v1/odata/"
    service = ODataAPI(url)
    service.describe()

