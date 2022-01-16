Expectativas
############

A API de expectativas divulgadas no boletim FOCUS pode ser acessada através da classe
:py:class:`bcb.Expectativas`.

.. _documentacao: https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/documentacao

__ documentacao_

Os dados são obtidos a partir da `API de Expectativas`__.

Integração com API de expectativas de mercado de cerca de 130
instituições do mercado financeiro participantes do
Sistema de Expectativas de Mercado para diversas variáveis
macroeconômicas.

Os dados são publicados no primeiro dia útil de cada semana.

Para períodos para os quais não haja estatísticas serão omitidos
na consulta.

São publicadas as expectativas informadas pelas instituições que
autorizaram a divulgação. As expectativas divulgadas possuem
defasagem de 1 ano.

Essa API tem sete *endpoints*

- ``ExpectativasMercadoTop5Anuais``: Expectativas de mercado anuais para
  os indicadores do Top 5
- ``ExpectativasMercadoInstituicoes``: Expectativas de mercado informadas
  pelas instituições credenciadas
- ``ExpectativaMercadoMensais``: Expectativas de Mercado Mensais
- ``ExpectativasMercadoInflacao12Meses``: Expectativas de mercado para
  inflação nos próximos 12 meses
- ``ExpectativasMercadoTop5Mensais``: Expectativas de mercado mensais para
  os indicadores do Top 5
- ``ExpectativasMercadoTrimestrais``: Expectativas de Mercado Trimestrais
- ``ExpectativasMercadoAnuais``: Expectativas de Mercado Anuais


Ao instanciar a classe :py:class:`bcb.Expectativas` diversas informações
são obtidas e a melhor maneira de interagir com a API é
através do método :py:meth:`bcb.Expectativas.describe`.

.. ipython:: python

    from bcb import Expectativas
    em = Expectativas()
    em.describe()

O método :py:meth:`bcb.Expectativas.describe` também recebe o nomes dos
*endpoints* e apresenta uma descrição do *endpoint* trazendo o seu tipo
`EntityType` e as propriedades retornadas `Properties` e os seus respectivos
tipos.

.. ipython:: python

    em.describe('ExpectativasMercadoTop5Anuais')

Esse *endpoint* retorna as colunas:

- Indicador
- Data
- DataReferencia
- tipoCalculo
- Media
- Mediana
- DesvioPadrao
- Minimo
- Maximo

Para obter os dados de um *endpoint* é necessário obtê-lo através do
método :py:meth:`bcb.Expectativas.get_endpoint` que retorna uma classe
:py:class:`bcb.Endpoint`.

.. ipython:: python

    ep = em.get_endpoint('ExpectativasMercadoTop5Anuais')

A partir desse *endpoint* executar uma consulta com o método :py:meth:`bcb.Endpoint.query`.

.. ipython:: python

    ep.query().limit(10).collect()


O método :py:meth:`bcb.Endpoint.query` retorna um objeto da classe
:py:class:`bcb.odata.ODataQuery` que possui diversas características
para a realização de consultas mais elaboradas.

Note que no exemplo acima foi utilizado o método ``limit`` que limita
a quantidade de resultados retornados, neste caso, em 10.

É possível realizar consultas mais elaboradas, por exemplo, filtrando pelo
indicador para que traga apenas informações do IPCA.

.. ipython:: python

    ep.query().filter(ep.Indicador == 'IPCA').limit(10).collect()


As consultas podem ficar ainda mais elaboradas, com diversos filtros,
ordenando colunas e selecionando as colunas na saída.

.. ipython:: python

    (ep.query()
     .filter(ep.Indicador == 'IPCA', ep.DataReferencia == 2023)
     .filter(ep.Data >= '2022-01-01')
     .filter(ep.tipoCalculo == 'C')
     .select(ep.Data, ep.Media, ep.Mediana)
     .orderby(ep.Data.desc())
     .limit(10)
     .collect())
