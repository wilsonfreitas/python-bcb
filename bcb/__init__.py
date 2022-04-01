
from .odata import ODataEntitySet, ODataFunctionImport, ODataQuery, \
    ODataPropertyFilter, ODataPropertyOrderBy, \
    ODataProperty, ODataService
import pandas as pd


OLINDA_BASE_URL = 'https://olinda.bcb.gov.br/olinda/servico'


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
    def collect(self):
        data = super().collect()
        return pd.DataFrame(data['value'])


class Endpoint(metaclass=EndpointMeta):
    def __init__(self, entity, url):
        self._entity = entity
        self._url = url

    def get(self, *args, **kwargs):
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
            if k == 'limit':
                _query.limit(val)
            elif k == 'skip':
                _query.skip(val)
            elif k == 'verbose':
                verbose = val
            else:
                _query.parameters(**{k: val})
        _query.format('application/json')

        if verbose:
            _query.show()
        data = _query.collect()
        _query.reset()
        return pd.DataFrame(data['value'])

    def query(self):
        return EndpointQuery(self._entity, self._url)


class BaseODataAPI:
    '''
    Classe que abstrai qualquer API OData

    Essa classe não deve ser acessada diretamente.
    '''
    def __init__(self):
        '''
        BaseODataAPI construtor
        '''
        self.service = ODataService(self.BASE_URL)

    def describe(self, endpoint=None):
        '''
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
        '''
        if endpoint:
            self.service[endpoint].describe()
        else:
            self.service.describe()

    def get_endpoint(self, endpoint):
        '''
        Obtem o *endpoint*

        Parameters
        ----------

        endpoint : str
            nome do endpoint

        Returns
        -------
        bcb.Endpoint
            Retorna o *endpoint* referente ao nome fornecido

        Raises
        ------
        ValueError
            Se o *endpoint* fornecido é errado.
        '''
        return Endpoint(self.service[endpoint], self.service.url)


class GenericODataAPI(BaseODataAPI):
    '''
    Classe que abstrai qualquer API OData

    Essa classe pode ser acessada diretamente passando
    uma URL válida para uma API OData.

    Uma boa alternativa para acessar APIs que ainda
    não possuem implementação específica.
    '''
    def __init__(self, url):
        '''
        GenericODataAPI construtor

        Parameters
        ----------

        url : str
            URL de API OData

            Em geral tem o padrão

            ``https://olinda.bcb.gov.br/olinda/servico/<serviço>/versao/v1/odata/``

            onde <serviço> é a implementação desejada, por exemplo:

            - Expectativas
            - PTAX
        '''
        self.service = ODataService(url)


class Expectativas(BaseODataAPI):
    '''
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
    '''
    BASE_URL = f'{OLINDA_BASE_URL}/Expectativas/versao/v1/odata/'


class PTAX(BaseODataAPI):
    '''
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
    '''
    BASE_URL = f'{OLINDA_BASE_URL}/PTAX/versao/v1/odata/'


class IFDATA(BaseODataAPI):
    '''
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
    '''
    BASE_URL = f'{OLINDA_BASE_URL}/IFDATA/versao/v1/odata/'


class TaxaJuros(BaseODataAPI):
    BASE_URL = f'{OLINDA_BASE_URL}/taxaJuros/versao/v2/odata/'


class MercadoImobiliario(BaseODataAPI):
    BASE_URL = f'{OLINDA_BASE_URL}/MercadoImobiliario/versao/v1/odata/'


class SPI(BaseODataAPI):
    BASE_URL = f'{OLINDA_BASE_URL}/SPI/versao/v1/odata/'


class TarifasBancariasPorInstituicaoFinanceira(BaseODataAPI):
    K = 'Informes_ListaTarifasPorInstituicaoFinanceira'
    BASE_URL = f'{OLINDA_BASE_URL}/{K}/versao/v1/odata/'


class TarifasBancariasPorServico(BaseODataAPI):
    K = 'Informes_ListaValoresDeServicoBancario'
    BASE_URL = f'{OLINDA_BASE_URL}/{K}/versao/v1/odata/'


class PostosAtendimentoEletronicoPorInstituicaoFinanceira(BaseODataAPI):
    K = 'Informes_PostosDeAtendimentoEletronico'
    BASE_URL = f'{OLINDA_BASE_URL}/{K}/versao/v1/odata/'


class PostosAtendimentoCorrespondentesPorInstituicaoFinanceira(BaseODataAPI):
    K = 'Informes_Correspondentes'
    BASE_URL = f'{OLINDA_BASE_URL}/{K}/versao/v1/odata/'


class EstatisticasSTR(BaseODataAPI):
    K = 'STR'
    BASE_URL = f'{OLINDA_BASE_URL}/{K}/versao/v1/odata/'


class DinheiroCirculacao(BaseODataAPI):
    K = 'mecir_dinheiro_em_circulacao'
    BASE_URL = f'{OLINDA_BASE_URL}/{K}/versao/v1/odata/'


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
