
OData
=====

Diversas classes implementam a integração com APIs OData.

- :py:class:`bcb.odata.api.Expectativas`
- :py:class:`bcb.odata.api.PTAX`
- :py:class:`bcb.odata.api.TaxaJuros`
- :py:class:`bcb.odata.api.IFDATA`
- :py:class:`bcb.odata.api.MercadoImobiliario`

Todas essas classes herdam de :py:class:`bcb.odata.api.BaseODataAPI` que faz a integração
com as APIs OData e organiza a informação em um ``DataFrame``.

Veja todas as APIs implementadas em :ref:`APIs OData`.

:py:class:`bcb.odata.api.BaseODataAPI`
--------------------------------------

A classe :py:class:`bcb.odata.api.BaseODataAPI` possui apenas 2 métodos:

- :py:meth:`bcb.odata.api.BaseODataAPI.describe`: imprime informações da API, como
  quais *endpoints* estão disponíveis. Passando o nome do *endpoint*
  o método imprime as informações do que é retornado pelo *endpoint* e
  o se há algum parâmetro necessário, caso seja uma função.
- :py:meth:`bcb.odata.api.BaseODataAPI.get_endpoint`: retorna um objeto
  :py:class:`bcb.odata.api.Endpoint` referente ao nome do *endpoint* fornecido.


:py:class:`bcb.odata.api.Endpoint`
----------------------------------

Os *endpoints* retornados herdam da classe :py:class:`bcb.odata.api.Endpoint`,
que possui o método :py:meth:`bcb.odata.api.Endpoint.query`, através do qual são
realizadas as consultas estruturadas na API OData.

:py:class:`bcb.odata.framework.ODataQuery`
------------------------------------------

:py:meth:`bcb.odata.api.Endpoints.query` retorna um objeto :py:class:`bcb.odata.framework.ODataQuery`
que possui os seguintes métodos.

- :py:meth:`bcb.odata.framework.ODataQuery.filter`
- :py:meth:`bcb.odata.framework.ODataQuery.select`
- :py:meth:`bcb.odata.framework.ODataQuery.orderby`
- :py:meth:`bcb.odata.framework.ODataQuery.limit`
- :py:meth:`bcb.odata.framework.ODataQuery.skip`
- :py:meth:`bcb.odata.framework.ODataQuery.parameters`
- :py:meth:`bcb.odata.framework.ODataQuery.collect`
- :py:meth:`bcb.odata.framework.ODataQuery.show`

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

    em.describe('ExpectativaMercadoMensais')


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

    ep = em.get_endpoint('ExpectativasMercadoTop5Anuais')

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

    ep.query().filter(ep.Indicador == 'IPCA').limit(10).collect()

Note que o *endpoint* tem como atributo ``Indicador`` que é uma
das colunas retornadas.
Todas as demais colunas podem ser acessadas através do objeto
``ep``.

Outra consulta mais elaborada com diversos filtros e ordenação e selecionando
um conjunto de colunas.

.. ipython:: python

    (ep.query()
     .filter(ep.Indicador == 'IPCA', ep.DataReferencia >= 2023)
     .filter(ep.Data >= '2022-01-01')
     .filter(ep.tipoCalculo == 'C')
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

    ptax.describe('CotacaoMoedaPeriodo')

Vemos que a função recebe três parâmetros: ``moeda``, ``dataInicial``,
``dataFinalCotacao``.
Estes parâmetros são passados para a consulta utilizando o método
``parameters``.

.. ipython:: python

    ep = ptax.get_endpoint('CotacaoMoedaPeriodo')
    (ep.query()
       .limit(10)
       .parameters(moeda='USD', dataInicial='01/01/2022', dataFinalCotacao='01/10/2022')
       .collect())


Fora os parâmetros, todos os demais métodos funcionam como esperado.
Podemos filtrar apenas pelos dados de abertura.

.. ipython:: python

    (ep.query()
       .limit(10)
       .filter(ep.tipoBoletim == 'Abertura')
       .parameters(moeda='USD', dataInicial='01/01/2022', dataFinalCotacao='01/10/2022')
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

