
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

    ep.query().limit(10).collect()

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
- :py:meth:`bcb.odata.framework.ODataQuery.skip`: *pula* os ``n`` primeiros registros da consulta.
- :py:meth:`bcb.odata.framework.ODataQuery.parameters`: *endpoints* do tipo ``FunctionImports`` possuem parâmetros que são definidos por este método.
- :py:meth:`bcb.odata.framework.ODataQuery.collect`: o *framework* tem uma abordagem *lazy*, dessa forma, este método realiza a consulta trazendo os dados e retornando um DataFrame.
- :py:meth:`bcb.odata.framework.ODataQuery.show`: imprime a estrutura da consulta.

Os métodos ``filter``, ``select``, ``orderby``, ``limit``, ``skip`` e ``parameters`` retornam o objeto
:py:class:`bcb.odata.framework.ODataQuery`, e isso permite a realização de chamadas aninhadas que compõem a consulta.

Por exemplo, na consulta do PIX, as datas não estão ordenadas, temos dias de 2021, 2022 e 2023 nos 10 registros
retornados.
Vamos ordernar pela propriedade ``Data`` de forma decrescente.

.. ipython:: python

    ep.query().orderby(ep.Data.desc()).limit(10).collect()

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
        .limit(10)
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
        .limit(10)
        .show())


Filtrando Dados
^^^^^^^^^^^^^^^

Os filtros são executados pelo método ``filter`` e aplicados às propriedades do *endpoint*, por isso é necessário
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
    query = ep.query().filter(ep.Indicador == 'IPCA').limit(10)
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
     .filter(ep.tipoCalculo == 'C'))
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
        .limit(10)
        .show())

O objeto ``datetime`` é formatado como data na consulta, note que não há aspas na definição do filtro.


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

Aplicações
----------

As APIs OData sem apresentam destas 2 maneiras:

- :ref:`EntitySets`: consultas estáticas sem parâmetros que retornam dados em formato tabular disponibilizados pela API.
  Exemplos de APIs: :ref:`Expectativas` e :ref:`Taxas de Juros`.
- :ref:`FunctionImports`: consultas dinâmicas com parâmetros  que retornam dados em formato tabular disponibilizados pela API.
  Um exemplo é a :ref:`API OData de Moedas`.

Identifica-se a maneira pela qual a API se apresenta utilizando o método :py:meth:`bcb.odata.api.BaseODataAPI.describe`
das classes que herdam :py:class:`bcb.odata.api.BaseODataAPI`.

API de Expectativas
^^^^^^^^^^^^^^^^^^^

A API de Expectativas possui diversos *entity sets*.
Utilizando o método ``describe`` visualizamos todos os *entity sets* disponibilizados pela API.

.. ipython:: python

    from bcb import Expectativas
    em = Expectativas()
    em.describe()

A API de Expectativas possui 8 ``EntitySets``.
Essa listagem traz os nomes dos ``EntitySets`` e ao passar um destes nomes para o método ``describe`` obtemos a
descrição do ``EntitySet`` que é o *endpoint* que dá acesso a API.

EntitySets
""""""""""

Cada ``EntitySet`` é um *endpoint* que retorna um conjunto de dados toda vez que são chamados.
Utilizamos os método ``describe`` para obter informações sobre o que é retornado na solicitação ao *endpoint*.

Inspecionando o *endpoint* ``ExpectativaMercadoMensais``

.. ipython:: python

    em.describe("ExpectativaMercadoMensais")


O *endpoint* ``ExpectativaMercadoMensais`` retorna um conjunto de dados
denominado ``br.gov.bcb.olinda.servico.Expectativas.ExpectativaMercadoMensal``, que é um ``EntityType``.
Este ``EntityType`` tem as seguintes propriedades:

- ``Indicador<str>``
- ``Data<str>``
- ``DataReferencia<str>``
- ``Media<float>``
- ``Mediana<float>``
- ``DesvioPadrao<float>``
- ``Minimo<float>``
- ``Maximo<float>``
- ``numeroRespondentes<int>``
- ``baseCalculo<int>``

Note que cada propriedade tem um tipo associado.
As propriedades são formatadas em colunas no DataFrame retornado como resultado da consulta.
É muito importante conhecer as colunas, pois caso se queira realizar filtros ou ordenação nas
consultas, estes são aplicados às propriedades.

    A utilização de filtros e ordenação na consulta é fundamental para a realização de consultas eficientes, pois estas
    operações são realizadas diretamente no processamento da API e isso reduz o volume de dados trafegados e,
    consequentemente, acelera a consulta.

Para realizar uma consulta é necessário obter um objeto da classe :py:class:`bcb.odata.api.Endpoint`.
Isso é feito chamando o método :py:meth:`bcb.odata.api.Expectativas.get_endpoint` com o nome do ``EntitySet`` desejado.
Vamos utilizar o *endpoint* ``ExpectativaMercadoMensais`` como exemplo.

.. ipython:: python

    ep = em.get_endpoint("ExpectativasMercadoTop5Anuais")

Tendo o objeto com o *endpoint* basta executar a consulta com ``query`` e
chamando ``collect`` ao fim para obter os dados.

.. ipython:: python

    ep.query().limit(10).collect()

Note que o método ``limit`` limita o retorno da consulta em 10 elementos.
Uma forma de avaliar a consulta sem executá-la é utilizando o método ``show``.

.. ipython:: python

    ep.query().limit(10).show()

Note que como apenas o ``limit`` foi utilizado, o único
parâmetro definido é o ``$top = 10`` indicando que apenas
10 elementos serão retornados.

Todos os métodos de :py:class:`bcb.odata.framework.ODataQuery` retornam a própria
instância do objeto, com excessão a ``show`` e ``collect``.
Por essa razão é possível realizar chamadas encadeadas configurando
a consulta.

Uma consulta mais elaborada com ``filter``.

.. ipython:: python

    ep.query().filter(ep.Indicador == "IPCA").limit(10).collect()

Note que o *endpoint* tem como atributo ``Indicador`` que é uma
das colunas retornadas.
Todas as demais colunas podem ser acessadas através do objeto
``ep``.

Outra consulta mais elaborada com diversos filtros e ordenação e selecionando
um conjunto de colunas.

.. ipython:: python

    (ep.query()
     .filter(ep.Indicador == "IPCA", ep.DataReferencia >= 2023)
     .filter(ep.Data >= "2022-01-01")
     .filter(ep.tipoCalculo == "C")
     .select(ep.Data, ep.DataReferencia, ep.Media, ep.Mediana)
     .orderby(ep.Data.desc(), ep.DataReferencia.asc())
     .limit(10)
     .collect())

API de Moedas
^^^^^^^^^^^^^

Uma outra aplicação é com a API de Moedas que implementa a especificação OData.
Utilizando a classe :py:class:`bcb.odata.api.PTAX` temos:

.. ipython:: python

    from bcb import PTAX
    ptax = PTAX()
    ptax.describe()


FunctionImports
"""""""""""""""

Note que essa API tem um ``EntitySet`` e seis ``FunctionImports``.
A diferença entre eles é que os ``FunctionImports`` são funções
e como funções recebem parâmetros que na maioria das vezes não são opicionais.

Executando ``describe`` na função ``CotacaoMoedaPeriodo`` temos:

.. ipython:: python

    ptax.describe("CotacaoMoedaPeriodo")

Vemos que a função recebe três parâmetros: ``moeda``, ``dataInicial``,
``dataFinalCotacao``.
Estes parâmetros são passados para a consulta utilizando o método
``parameters``.

.. ipython:: python

    ep = ptax.get_endpoint("CotacaoMoedaPeriodo")
    (ep.query()
       .limit(10)
       .parameters(moeda="USD", dataInicial="01/01/2022", dataFinalCotacao="01/10/2022")
       .collect())


Fora os parâmetros, todos os demais métodos funcionam como esperado.
Podemos filtrar apenas pelos dados de abertura.

.. ipython:: python

    (ep.query()
       .limit(10)
       .filter(ep.tipoBoletim == "Abertura")
       .parameters(moeda="USD", dataInicial="01/01/2022", dataFinalCotacao="01/10/2022")
       .collect())


Classe ODataAPI
^^^^^^^^^^^^^^^

O portal de Dados Abertos to Banco Central apresenta diversas APIs OData, são
dezenas de APIs disponíveis.
A URL com metadados de cada API pode ser obtida no portal.
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

Conclusão
---------

Esta estrutura se aplica a todas as classes que fazem interface com APIs
que implementam a especificação OData.

Para conhecer a API, além de ler a documentação, basta executar os passos:

- instanciar a classe
- executar o ``describe`` para conhecer os *endpoints*
- executar o ``describe`` para um dos *endpoints* e saber o que precisa ser
  fornecido e o que será retornado
- obter o *endpoint* com ``get_endpoint``
- tendo o *endpoint* executar ``query`` e não esquecer de chamar ``collect`` ao fim

