
APIs OData
==========

Diversas classes implementam a integração com APIs OData.

- :py:class:`bcb.Expectativas`
- :py:class:`bcb.PTAX`
- :py:class:`bcb.TaxaJuros`
- :py:class:`bcb.IFDATA`
- :py:class:`bcb.MercadoImobiliario`

Todas essas classes herdam de :py:class:`bcb.BaseODataAPI` que faz a integração
com as APIs OData e organiza a informação em um ``DataFrame``.

:py:class:`bcb.BaseODataAPI`
----------------------------

A classe :py:class:`bcb.BaseODataAPI` possui apenas 2 métodos:

- :py:meth:`bcb.BaseODataAPI.describe`: imprime informações da API, como
  quais *endpoints* estão disponíveis. Passando o nome do *endpoint*
  o método imprime as informações do que é retornado pelo *endpoint* e
  o se há algum parâmetro necessário, caso seja uma função.
- :py:meth:`bcb.BaseODataAPI.get_endpoint`: imprime informações da API, como
  quais *endpoints* estão disponíveis.

:py:class:`bcb.Endpoint`
------------------------

Os *endpoints* retornados herdam da classe :py:class:`bcb.Endpoint`,
que possui o método :py:meth:`bcb.Endpoint.query`, através do qual é
possível realizar as consultas estruturadas na API OData.

:py:class:`bcb.odata.ODataQuery`
--------------------------------

:py:meth:`bcb.Endpoints.query` retorna um objeto :py:class:`bcb.odata.ODataQuery`
que possui os seguintes métodos.

- :py:meth:`bcb.odata.ODataQuery.filter`
- :py:meth:`bcb.odata.ODataQuery.select`
- :py:meth:`bcb.odata.ODataQuery.orderby`
- :py:meth:`bcb.odata.ODataQuery.limit`
- :py:meth:`bcb.odata.ODataQuery.skip`
- :py:meth:`bcb.odata.ODataQuery.parameters`
- :py:meth:`bcb.odata.ODataQuery.collect`
- :py:meth:`bcb.odata.ODataQuery.show`

Aplicações
----------

Expectativas
^^^^^^^^^^^^

Vamos ver como isso tudo funciona utilizando a API de expectativas.

.. ipython:: python

    from bcb import Expectativas
    em = Expectativas()
    em.describe()

``EntitySets``
""""""""""""""

Vemos que na API de expectativas tem uma listagem de ``EntitySets``.
``EntitySets`` são *endpoints* que retornam um conjunto de dados toda vez que
são chamados.

Inspecionando o *endpoint* ``ExpectativaMercadoMensais``

.. ipython:: python

    em.describe('ExpectativaMercadoMensais')


``EntityType``
""""""""""""""

Os dados retornados por um ``EntitySet`` tem um tipo que é o seu ``EntityType``.
Para o *endpoint* ``ExpectativaMercadoMensais`` o tipo retornado é
``br.gov.bcb.olinda.servico.Expectativas.ExpectativaMercadoMensal`` que retorna as
seguintes colunas (com seus respectivos tipos):

- Indicador<str>
- Data<str>
- DataReferencia<str>
- Media<float>
- Mediana<float>
- DesvioPadrao<float>
- Minimo<float>
- Maximo<float>
- numeroRespondentes<int>
- baseCalculo<int>

É muito importante conhecer as colunas caso queira realizar filtros ou ordenação nas
consultas.

Para realizar a consulta é necessário obter o objeto :py:class:`bcb.Endpoint`.
Isso é feito executando o método :py:meth:`bcb.Expectativas.get_endpoint`.

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

Todos os métodos de :py:class:`bcb.odata.ODataQuery` retornam a própria
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

Moedas
^^^^^^

Uma outra aplicação é com a API de Moedas que implementa a especificação OData.
Utilizando a classe :py:class:`bcb.PTAX` temos:

.. ipython:: python

    from bcb import PTAX
    ptax = PTAX()
    ptax.describe()


``FunctionImports``
"""""""""""""""""""

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

.. currentmodule:: bcb

.. autoclass:: ODataAPI
    :inherited-members:

O portal de Dados Abertos to Banco Central apresenta diversas APIs OData, são
dezenas de APIs disponíveis.
A URL com metadados de cada API pode ser obtida no portal.
A classe ``ODataAPI`` permite acessar qualquer API Odata de posse da sua URL.

Por exemplo, a API de estatísticas de operações registradas no Selic tem a seguinte URL::

    https://olinda.bcb.gov.br/olinda/servico/selic_operacoes/versao/v1/odata/

que pode ser obtida no portal de dados abertos no `link <https://dadosabertos.bcb.gov.br/dataset/estatisticas-selic-operacoes>`_.

Essa API pode ser diretamente acessada através da classe ``ODataAPI``.

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

