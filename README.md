# python-bcb

**python-bcb** é uma interface em Python estruturada para obter informações
da API de dados abertos do [Banco Central do Brasil](https://www.bcb.gov.br).

[![Downloads](https://img.shields.io/pypi/dm/python-bcb.svg)](https://pypi.python.org/pypi/python-bcb/)
[![image](https://img.shields.io/pypi/v/python-bcb.svg?color=green)](https://pypi.python.org/pypi/python-bcb/)
![Test workflow](https://github.com/wilsonfreitas/python-bcb/actions/workflows/test.yml/badge.svg)
![Lint workflow](https://github.com/wilsonfreitas/python-bcb/actions/workflows/lint.yml/badge.svg)
![Sphinx workflow](https://github.com/wilsonfreitas/python-bcb/actions/workflows/sphinx.yml/badge.svg)


O projeto de [Dados Abertos do Banco Central do Brasil](https://dadosabertos.bcb.gov.br/)
disponibiliza diversas APIs provendo acesso direto a dados de:

* Moedas
* Taxas de Juros
* Índices de preços
* Informações de Instituições Financeiras
* Expectativas do Mercado (Expectativas do Boletim FOCUS)
* E muito outros ...

# Instalação

**python-bcb** está disponível no [Python Package Index](https://pypi.org/project/python-bcb/) e pode ser instalado via `pip` usando.

```shell
pip install python-bcb
```

# APIs


## SGS
Utiliza o webservice do SGS
([Sistema Gerenciador de Séries Temporais](https://www3.bcb.gov.br/sgspub/))
para obter os dados.

## Conversor de Moedas

Implementado no módulo `currency`, um conjunto de funções que realiza webscraping
no site do [Conversor de Moedas](https://www.bcb.gov.br/conversao)
do Banco Central, possível obter séries temporais de frequência diária
de diversas moedas.

## Moedas OData

O Banco Central disponibiliza diversas informações em APIs que
seguem o padrão [OData](https://odata.org).
A classe `bcb.PTAX` implementa uma API OData que
entrega os boletins diários de taxas de câmbio do Banco Central.
Esta API entrega mais informações do que o que é obtido no
`Conversor de Moedas`.

## Expectativas

A API de Expectativas de Mercado traz todas as estatísticas das variáveis
macroeconômicas fornecidos por um conjuto de instituições do mercado
financeiro.
A classe `bcb.Expectativas` implementa essa interface no
padrão OData.

# Which Module Should I Use?

Use this table to choose the right module for your use case:

| Use Case | Module | Key Features |
|----------|--------|--------------|
| Daily time series (inflation, interest rates) | `bcb.sgs` | Largest historical dataset, granular frequency control, multiple pre-defined series |
| Daily foreign exchange rates (PTAX) | `bcb.currency` | Bid/ask spreads, quick implementation, daily frequency |
| Market expectations (FOCUS survey) | `bcb.odata` (Expectativas) | Forward-looking economic indicators, consensus forecasts |
| Interest rates (various types) | `bcb.odata` (TaxaJuros) | Detailed rate curves, real estate lending rates |
| Real estate financing data | `bcb.odata` (MercadoImobiliario) | Mortgage originations, average rates, volumes |
| Financial institution information | `bcb.odata` (IFDATA) | Bank balance sheet data, regulatory information |
| Advanced data analysis with filters | `bcb.odata` (any service) | Chainable API, SQL-like filtering, sorting, selection |
| Concurrent data fetching | Any module with `async_get()` | Non-blocking requests, improved performance for bulk operations |

# Quick Start

## Time Series with SGS

```python
from bcb import sgs

# Fetch SELIC rate (code 1)
df = sgs.get(1, start="2023-01-01", end="2024-12-31")
```

## Exchange Rates with Currency

```python
from bcb import currency

# Fetch USD bid/ask prices
usd = currency.get("USD", start="2023-01-01", end="2024-12-31")
```

## Market Expectations with OData

```python
from bcb import Expectativas

api = Expectativas()
endpoint = api.get_endpoint("ExpectativasMercadoAnuais")

# Get IPCA forecasts
df = endpoint.query().filter(endpoint.Indicador == "IPCA").limit(100).collect()
```

# FAQ

## Q: What's the difference between SGS and PTAX currency data?
**A:** SGS contains mostly economic indicators. For currency exchange rates, use `bcb.currency` (PTAX data) for daily rates or `bcb.odata` PTAX service for detailed institutional data. The currency module is simpler for common use cases.

## Q: How far back does historical data go?
**A:** It varies by series:
- SGS: Most series go back to 1980s or 1990s (check specific code documentation)
- Currency: Daily rates available from approximately 1980
- OData services: Varies; check BCB documentation for specific endpoints

## Q: Can I fetch data asynchronously?
**A:** Yes! All modules have `async_get()` or similar async methods. Use them for concurrent requests:
```python
import asyncio
from bcb import sgs

async def main():
    results = await asyncio.gather(
        sgs.async_get(1),  # SELIC
        sgs.async_get(433),  # IPCA
    )

asyncio.run(main())
```

## Q: How do I handle errors/missing data?
**A:** The library raises specific exceptions:
- `CurrencyNotFoundError`: Currency symbol not found
- `SGSError`: SGS service error
- `BCBRateLimitError`: Rate limit exceeded (HTTP 429)
- `BCBAPIError`: Other API errors

```python
from bcb import sgs
from bcb.exceptions import SGSError, BCBRateLimitError

try:
    df = sgs.get(99999)  # Invalid code
except SGSError as e:
    print(f"Data error: {e}")
except BCBRateLimitError:
    print("Rate limited - please try again later")
```

## Q: How do I enable logging to debug requests?
**A:** The library uses Python's standard logging module:
```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("bcb")
logger.setLevel(logging.DEBUG)

# Now all HTTP requests/responses will be logged
```

## Q: Is there caching to avoid redundant requests?
**A:** Yes:
- `bcb.currency`: Automatic in-memory cache of currency lists
- `bcb.odata`: OData metadata cached per service URL
- Call `currency.clear_cache()` to reset if data changes

## Q: Can I use this in a long-running application?
**A:** Yes, but be mindful of:
- Rate limits: BCB APIs may have limits; implement backoff if needed
- Caching: Currency cache persists in memory; clear it if data updates matter
- Connection pooling: Uses httpx with connection pooling by default
- Async API: Use async methods for truly non-blocking behavior

## Q: How do I contribute or report issues?
**A:** Visit the [GitHub repository](https://github.com/wilsonfreitas/python-bcb) to:
- Report bugs
- Request features
- Submit pull requests
- View documentation

## Q: Where can I find more detailed documentation?
**A:**
- [API Documentation](https://bcb-python.readthedocs.io/)
- [Examples Directory](./examples/)
- Inline docstrings: `help(bcb.sgs.get)`, `help(bcb.currency.get)`, etc.
- [BCB Open Data Portal](https://dadosabertos.bcb.gov.br/)
