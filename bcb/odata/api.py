from .framework import (
    ODataEntitySet,
    ODataFunctionImport,
    ODataQuery,
    ODataPropertyFilter,
    ODataPropertyOrderBy,
    ODataProperty,
    ODataService,
)
import pandas as pd

OLINDA_BASE_URL = "https://olinda.bcb.gov.br/olinda/servico"


class EndpointMeta(type):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __call__(self, *args):
        obj = super().__call__(*args)
        entity = args[0]
        if isinstance(entity, ODataEntitySet):
            for name, prop in entity.entity.properties.items():
                setattr(obj, name, prop)
        elif isinstance(entity, ODataFunctionImport):
            for name, prop in entity.entity_set.entity.properties.items():
                setattr(obj, name, prop)
        return obj


class EndpointQuery(ODataQuery):
    _DATE_COLUMN_NAMES_BY_ENDPOINT = {
        "IfDataCadastro": {"Data": "%Y%m"}
    }
    _DATE_COLUMN_NAMES = {
        "Data",
        "dataHoraCotacao",
        "InicioPeriodo",
        "FimPeriodo",
        "DataVigencia",
    }

    def collect(self):
        raw_data = super().collect()
        data = pd.DataFrame(raw_data["value"])
        if not self._raw:
            for col in self._DATE_COLUMN_NAMES:
                if self.entity.name in self._DATE_COLUMN_NAMES_BY_ENDPOINT and col in self._DATE_COLUMN_NAMES_BY_ENDPOINT[self.entity.name]:
                    data[col] = pd.to_datetime(data[col], format=self._DATE_COLUMN_NAMES_BY_ENDPOINT[self.entity.name][col])
                elif col in data.columns:
                    data[col] = pd.to_datetime(data[col])
        return data


class Endpoint(metaclass=EndpointMeta):
    """
    Classe que representa os tipos de *endpoints* de APIs OData.

    As APIs OData têm 2 tipos de *endpoints*: *entity sets* e *functions imports*.
    Esta classe provê todos os mecanismos para acessar tanto os *entity sets* quanto os *functions imports* e
    realizar consultas em através de suas APIs de maneira transparente.

    Esta classe não deveria ser instanciada diretamente.
    Objetos dessa classe são retornados pelo método
    :py:meth:`bcb.odata.api.BaseODataAPI.get_endpoint` das classes que herdam
    :py:class:`bcb.odata.api.BaseODataAPI`.
    """
    def __init__(self, entity, url):
        """
        Construtor da classe Endpoint.

        Parameters
        ----------
        entity : bcb.odata.api.ODataEntity
            Objeto que representa um *entity set* ou um *function import*.
            Obtidos da classe ``bcb.odata.framework.ODataService``.
        url : str
            URL da API OData.
        """
        self._entity = entity
        self._url = url

    def get(self, *args, **kwargs):
        """
        Executa a consulta na API OData e retorna o resultado.

        Parameters
        ----------
        *args : argumentos para a consulta

        **kwargs : argumentos para a consulta

        Returns
        -------
        pd.DataFrame: resultado da consulta
        """
        _query = EndpointQuery(self._entity, self._url)
        for arg in args:
            if isinstance(arg, ODataPropertyFilter):
                _query.filter(arg)
            elif isinstance(arg, ODataPropertyOrderBy):
                _query.orderby(arg)
            elif isinstance(arg, ODataProperty):
                _query.select(arg)
        verbose = False
        for k, val in kwargs.items():
            if k == "limit":
                _query.limit(val)
            elif k == "skip":
                _query.skip(val)
            elif k == "verbose":
                verbose = val
            else:
                _query.parameters(**{k: val})
        _query.format("application/json")

        if verbose:
            _query.show()
        data = _query.collect()
        _query.reset()
        return data

    def query(self):
        """
        Retorna uma instância de EndpointQuery através da qual se construirá a consulta na API OData.

        Returns
        -------
        bcb.odata.api.EndpointQuery
        """
        return EndpointQuery(self._entity, self._url)


class BaseODataAPI:
    """
    Classe que abstrai qualquer API OData

    Essa classe não deve ser acessada diretamente.
    """

    def __init__(self):
        """
        BaseODataAPI construtor
        """
        self.service = ODataService(self.BASE_URL)

    def describe(self, endpoint=None):
        """
        Mostra a descrição de uma API ou de um *endpoint*
        específico.

        Parameters
        ----------

        endpoint : None (padrão) ou str
            nome do *endpoint*

        Returns
        -------

        Não retorna variável e imprime na tela uma descrição da API
        ou do *endpoint*.
        """
        if endpoint:
            self.service[endpoint].describe()
        else:
            self.service.describe()

    def get_endpoint(self, endpoint):
        """
        Obtem o *endpoint*

        Parameters
        ----------

        endpoint : str
            nome do endpoint

        Returns
        -------
        bcb.odata.api.Endpoint
            Retorna o *endpoint* referente ao nome fornecido

        Raises
        ------
        ValueError
            Se o *endpoint* fornecido é errado.
        """
        return Endpoint(self.service[endpoint], self.service.url)


class ODataAPI(BaseODataAPI):
    """
    Classe que abstrai qualquer API OData

    Essa classe pode ser acessada diretamente passando
    uma URL válida para uma API OData.

    Uma boa alternativa para acessar APIs que ainda
    não possuem implementação específica.
    """

    def __init__(self, url):
        """
        Parameters
        ----------

        url : str
            URL de API OData

            Em geral tem o padrão

            ``https://olinda.bcb.gov.br/olinda/servico/<serviço>/versao/v1/odata/``

            onde <serviço> é a implementação desejada, por exemplo:

            - Expectativas
            - PTAX
        """
        self.service = ODataService(url)


class Expectativas(BaseODataAPI):
    """
    Integração com API OData de Expectativas de Mercado.

    Cerca de 130
    instituições do mercado financeiro participantes do
    Sistema de Expectativas de Mercado para diversas variáveis
    macroeconômicas.

    Os dados são publicados no primeiro dia útil de cada semana.

    Esta interface possibilida a realização de consultas na
    API OData utilizando diversas funcionalidades presentes
    na especificação.

    Para períodos para os quais não haja estatísticas serão omitidos
    na consulta.

    São publicadas as expectativas informadas pelas instituições que
    autorizaram a divulgação.

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
    """

    BASE_URL = f"{OLINDA_BASE_URL}/Expectativas/versao/v1/odata/"


class PTAX(BaseODataAPI):
    """
    Integração com API OData de cotações diárias de taxas de câmbio.

    Essa API possui os seguintes *endpoints*:

    - ``Moedas``: Retorna a lista de moedas que podem ser usadas
    - ``CotacaoMoedaPeriodoFechamento``: Retorna os boletins diários com a
      Paridade de Compra e a Paridade de Venda no Fechamento.
    - ``CotacaoMoedaAberturaOuIntermediario``: Retorna os boletins diários
      com a Paridade de Compra e a Paridade de Venda na abertura e
      para instantes ao longo do dia (intermediários).
    - ``CotacaoMoedaDia``: Consulta dos boletins por dia para moeda
      especificada.
    - ``CotacaoMoedaPeriodo``: Consulta dos boletins por período para
      moeda especificada.
    - ``CotacaoDolarDia``: Consulta dos boletins de dólar por dia.
    - ``CotacaoDolarPeriodo``: Consulta dos boletins de dólar por período.

    Os boletins diários são divulgados diariamente e trazem 5 cotações
    para cada data: uma de abertura, três intermediários e uma de fechamento.

    Estes dados estão disponíveis desde 1984-11-28 e são referentes às taxas
    administradas, até março de 1990, e às taxas livres, a partir de então
    (Resolução 1690, de 18.3.1990).
    As taxas administradas são aquelas fixadas pelo Banco Central,
    a partir de março de 1992, essa taxa recebeu a denominação de taxa
    PTAX (fechamento).
    Até 30 de junho de 2011, as taxas livres correspondiam à média das taxas
    efetivas de operações no mercado interbancário, ponderada pelo volume de
    transações do dia.
    A partir de 1 de julho de 2011 (Circular 3506, de 2010-09-23), a Ptax
    passou a corresponder à média aritmética das taxas obtidas em quatro
    consultas diárias aos dealers de câmbio e refletem a taxa negociada no
    momento de abertura da janela de consulta.
    O boletim de fechamento PTAX corresponde à média aritmética das taxas dos
    boletins do dia.
    """

    BASE_URL = f"{OLINDA_BASE_URL}/PTAX/versao/v1/odata/"


class IFDATA(BaseODataAPI):
    """
    Integração com API OData para dados selecionados de instituições
    financeiras

    Dados selecionados de instituições financeiras dos relatórios do IFData
    disponibilizados na página https://www3.bcb.gov.br/ifdata/ em formato de
    dados abertos.
    No IFData são divulgadas trimestralmente informações das instituições
    autorizadas a funcionar e que estejam em operação normal.
    Os relatórios trimestrais são disponibilizados 60 dias após o fechamento
    das datas-bases março, junho e setembro, e 90 dias após o
    fechamento da data-base dezembro.
    """

    BASE_URL = f"{OLINDA_BASE_URL}/IFDATA/versao/v1/odata/"


class TaxaJuros(BaseODataAPI):
    """
    Taxas de juros de operações de crédito por instituição financeira - Médias
    dos últimos 5 dias

    As taxas de juros por instituição financeira apresentadas nesse conjunto de
    tabelas representam médias aritméticas das taxas de juros pactuadas nas
    operações realizadas nos cinco dias úteis referidos em cada publicação,
    ponderadas pelos respectivos valores contratados.

    Essas taxas de juros representam o custo efetivo médio das operações de
    crédito para os clientes, composto pelas taxas de juros efetivamente
    praticadas pelas instituições financeiras em suas operações de crédito,
    acrescidas dos encargos fiscais e operacionais incidentes sobre as
    operações.

    As taxas de juros apresentadas correspondem à média das taxas praticadas
    nas diversas operações realizadas pelas instituições financeiras em cada
    modalidade de crédito. Em uma mesma modalidade, as taxas de juros diferem
    entre clientes de uma mesma instituição financeira e variam de acordo com
    diversos fatores de risco envolvidos nas operações, tais como o valor e a
    qualidade das garantias apresentadas na contratação do crédito, o valor do
    pagamento dado como entrada da operação, o histórico e a situação cadastral
    de cada cliente, o prazo da operação, entre outros.

    Eventualmente algumas instituições financeiras não aparecem relacionadas
    nas tabelas em razão de não terem realizado operações de crédito nas
    respectivas modalidades nos períodos referidos ou por não terem prestado
    as informações requeridas pelo Banco Central do Brasil no prazo previsto
    pela legislação em vigor.

    A partir de abril de 2017, as taxas médias das operações de cartão de
    crédito rotativo passaram a ser publicadas de forma desagregada nas
    modalidades cartão de crédito rotativo regular - que compreende os
    financiamentos dos saldos remanescentes das faturas de cartão de crédito
    nos quais os clientes efetuam o pagamento mínimo requerido pela legislação
    em vigor - e cartão de crédito não regular , que compreende os
    financiamentos dos saldos remanescentes das faturas de cartão de crédito
    nos quais os clientes não efetuam o pagamento mínimo, sendo considerados
    em atraso.

    O Banco Central do Brasil não assume nenhuma responsabilidade por
    defasagem, erro ou outra deficiência em informações prestadas para fins de
    apuração das taxas médias apresentadas nesse conjunto de tabelas, cujas
    fontes sejam externas a esta instituição, bem como por quaisquer perdas ou
    danos decorrentes de seu uso.
    """

    BASE_URL = f"{OLINDA_BASE_URL}/taxaJuros/versao/v2/odata/"


class MercadoImobiliario(BaseODataAPI):
    """
    Informações do Mercado Imobiliário

    O Banco Central do Brasil divulga mensalmente informações sobre o mercado
    imobiliário. Os relatórios são atualizados no último dia útil do mês,
    disponibilizando os dados após 60 dias do fechamento de cada período.
    A publicação é o resultado da análise das informações recebidas através do
    Sistema de Informações de Créditos – SCR, Sistema de Informações
    Contábeis – Cosif, Direcionamento dos Depósitos de Poupança - RCO e das
    entidades de depósito e registro de ativos. Distribuídas em 6 seções,
    possuem informações sobre as fontes de recursos, direcionamento dos
    recursos da caderneta de poupança, valores contábeis, operações de crédito,
    detalhes dos imóveis financiados e índices relacionados com o setor.
    O relatório disponibiliza mais de 4.000 séries mensais em formato de dados
    abertos. As seções Crédito e Imóveis possuem detalhamentos por estados.
    """

    BASE_URL = f"{OLINDA_BASE_URL}/MercadoImobiliario/versao/v1/odata/"


class SPI(BaseODataAPI):
    """
    Estatísticas do SPI - Sistema de Pagamentos Instantâneos

    Estatísticas das movimentações financeiras transitadas no SPI (Sistema de
    Pagamentos Instantâneos) processadas por meio de lançamentos nas contas PI
    mantidas pelos participantes no Banco Central.
    """

    BASE_URL = f"{OLINDA_BASE_URL}/SPI/versao/v1/odata/"


class TarifasBancariasPorInstituicaoFinanceira(BaseODataAPI):
    """
    Tarifas Bancárias - por Segmento e por Instituição

    Esta API disponibiliza as informações mais recentes sobre as tarifas
    cobradas por instituições financeiras, por Segmento e por Instituição.
    """

    K = "Informes_ListaTarifasPorInstituicaoFinanceira"
    BASE_URL = f"{OLINDA_BASE_URL}/{K}/versao/v1/odata/"


class TarifasBancariasPorServico(BaseODataAPI):
    """
    Tarifas Bancárias - valores mínimos, máximos e médios por serviço

    Esta API disponibiliza as informações mais recentes sobre as tarifas
    cobradas por instituições financeiras, valores mínimos, máximos e médios
    por serviço.
    """

    K = "Informes_ListaValoresDeServicoBancario"
    BASE_URL = f"{OLINDA_BASE_URL}/{K}/versao/v1/odata/"


class PostosAtendimentoEletronicoPorInstituicaoFinanceira(BaseODataAPI):
    """
    Postos de Atendimento Eletrônico de Instituições Supervisionadas pelo Bacen

    Os arquivos disponíveis para transferência apresentam as informações mais
    atuais dos postos de atendimento eletrônico de Instituições Supervisionadas
    pelo Banco Central.
    """

    K = "Informes_PostosDeAtendimentoEletronico"
    BASE_URL = f"{OLINDA_BASE_URL}/{K}/versao/v1/odata/"


class PostosAtendimentoCorrespondentesPorInstituicaoFinanceira(BaseODataAPI):
    """
    Correspondentes no país

    O arquivo disponibilizado apresenta os dados mais atuais dos pontos de
    atendimento dos correspondentes, por instituição financeira e por
    município, com a identificação dos tipos de serviços prestados, conforme
    descrito na Resolução 3.954.
    """

    K = "Informes_Correspondentes"
    BASE_URL = f"{OLINDA_BASE_URL}/{K}/versao/v1/odata/"


class EstatisticasSTR(BaseODataAPI):
    """
    Estatísticas do STR - Sistema de Transferência de Reservas

    Estatísticas das movimentações financeiras transitadas no STR (Sistema de
    Transferência de Reservas) processadas por meio de lançamentos nas contas
    mantidas pelos participantes no Banco Central.
    """

    K = "STR"
    BASE_URL = f"{OLINDA_BASE_URL}/{K}/versao/v1/odata/"


class DinheiroCirculacao(BaseODataAPI):
    """
    Dinheiro em Circulação

    Registros diários das quantidades de cédulas e moedas em circulação (não
    estão incluídas as moedas comemorativas). As informações estão separadas
    para cada espécie (cédula ou moeda), família (categoria) e denominação do
    Real (símbolos : R$, BRL).
    """

    K = "mecir_dinheiro_em_circulacao"
    BASE_URL = f"{OLINDA_BASE_URL}/{K}/versao/v1/odata/"


# /Informes_Ouvidorias/versao/v1/odata/
# /RankingOuvidorias/versao/v1/odata/
# /Informes_ListaTarifasPorInstituicaoFinanceira/versao/v1/odata/
# /PoliticaMonetaria_TitulosOperacoesConjugadas/versao/v1/odata/
# /selic_contas/versao/v1/odata/
# /selic_clientes/versao/v1/odata/
# /Informes_FiliaisAdministradorasConsorcios/versao/v1/odata/
# /Informes_Agencias/versao/v1/odata/
# /SML/versao/v1/odata/
# /DASFN/versao/v1/odata/
