
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


class BaseAPI:

    def __init__(self):
        self.service = ODataService(self.BASE_URL)

    def describe(self, endpoint=None):
        if endpoint:
            self.service[endpoint].describe()
        else:
            self.service.describe()

    def get_endpoint(self, endpoint):
        return Endpoint(self.service[endpoint], self.service.url)


class Expectativas(BaseAPI):
    BASE_URL = f'{OLINDA_BASE_URL}/Expectativas/versao/v1/odata/'


class PTAX(BaseAPI):
    BASE_URL = f'{OLINDA_BASE_URL}/PTAX/versao/v1/odata/'


class IFDATA(BaseAPI):
    BASE_URL = f'{OLINDA_BASE_URL}/IFDATA/versao/v1/odata/'


class TaxaJuros(BaseAPI):
    BASE_URL = f'{OLINDA_BASE_URL}/taxaJuros/versao/v1/odata/'


class MercadoImobiliario(BaseAPI):
    BASE_URL = f'{OLINDA_BASE_URL}/MercadoImobiliario/versao/v1/odata/'


class SPI(BaseAPI):
    BASE_URL = f'{OLINDA_BASE_URL}/SPI/versao/v1/odata/'


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
