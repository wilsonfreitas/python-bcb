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
* E muito mais...

## Instalação

**python-bcb** está disponível no [Python Package Index](https://pypi.org/project/python-bcb/) e pode ser instalado via `pip`.

```shell
pip install python-bcb
```

## APIs

### SGS - Sistema Gerenciador de Séries Temporais

Utiliza o webservice do SGS ([Sistema Gerenciador de Séries Temporais](https://www3.bcb.gov.br/sgspub/)) para obter dados históricos de indicadores econômicos. Oferece a maior base de dados históricos com diversas séries temporais.

### Conversor de Moedas

Implementado no módulo `currency`, realiza webscraping no site do [Conversor de Moedas](https://www.bcb.gov.br/conversao) do Banco Central. Fornece séries temporais de frequência diária de taxas de câmbio (cotações de compra e venda).

### OData - APIs Estruturadas

O Banco Central disponibiliza diversas informações em APIs que seguem o padrão [OData](https://odata.org). Inclui:
- **PTAX**: Boletins diários de taxas de câmbio com dados institucionalmente detalhados
- **Expectativas**: Expectativas de mercado coletadas do Boletim FOCUS
- **TaxaJuros**: Diversas taxas de juros (Selic, CDI, Cheque especial, etc.)
- **MercadoImobiliario**: Dados de financiamento imobiliário
- **IFDATA**: Informações de instituições financeiras
- **SPI**: Sistema de Pagamentos Instantâneos

## Qual Módulo Devo Usar?

Use esta tabela para escolher o módulo certo para seu caso de uso:

| Caso de Uso | Módulo | Características Principais |
|----------|--------|--------------|
| Séries temporais diárias (inflação, taxas de juros) | `bcb.sgs` | Maior base histórica, controle granular de frequência, múltiplas séries pré-definidas |
| Taxas de câmbio diárias (PTAX) | `bcb.currency` | Spreads de compra/venda, implementação rápida, frequência diária |
| Expectativas de mercado (Boletim FOCUS) | `bcb.odata` (Expectativas) | Indicadores de expectativas, previsões de consenso |
| Taxas de juros (diversos tipos) | `bcb.odata` (TaxaJuros) | Curvas detalhadas, taxas de financiamento imobiliário |
| Dados de financiamento imobiliário | `bcb.odata` (MercadoImobiliario) | Originações, taxas médias, volumes |
| Informações de instituições financeiras | `bcb.odata` (IFDATA) | Dados de balanço, informações regulatórias |
| Análise de dados avançada com filtros | `bcb.odata` (qualquer serviço) | API encadeável, filtragem tipo SQL, ordenação, seleção |
| Busca concorrente de dados | APIs assíncronas (`sgs`, `currency` e OData) | Requisições não-bloqueantes com `async_get()`, `Endpoint.async_get()` e `ODataQuery.async_collect()` |

## Início Rápido

### Séries Temporais com SGS

```python
from bcb import sgs

# Buscar taxa Selic (código 1)
df = sgs.get(1, start="2023-01-01", end="2024-12-31")
```

### Taxas de Câmbio com Currency

```python
from bcb import currency

# Buscar preços de compra/venda do USD
usd = currency.get("USD", start="2023-01-01", end="2024-12-31")
```

### Expectativas de Mercado com OData

```python
from bcb import Expectativas

api = Expectativas()
endpoint = api.get_endpoint("ExpectativasMercadoAnuais")

# Obter previsões do IPCA
df = endpoint.query().filter(endpoint.Indicador == "IPCA").limit(100).collect()
```

## Perguntas Frequentes

### P: Qual é a diferença entre dados de moedas do SGS e PTAX?
**R:** SGS contém principalmente indicadores econômicos. Para taxas de câmbio, use `bcb.currency` (dados PTAX) para cotações diárias ou o serviço `bcb.odata` PTAX para dados institucionais detalhados. O módulo currency é mais simples para casos comuns.

### P: Quão longe no tempo os dados históricos vão?
**R:** Varia por série:
- SGS: Maioria das séries remontam aos anos 1980/1990 (verifique documentação específica do código)
- Currency: Cotações diárias disponíveis desde aproximadamente 1980
- Serviços OData: Varia; consulte documentação BCB para endpoints específicos

### P: Posso buscar dados de forma assíncrona?
**R:** Sim. SGS e currency oferecem `async_get()`, e os endpoints OData oferecem `async_get()` e `async_collect()`. Feche o cliente assíncrono ao final de aplicações de longa duração:
```python
import asyncio
from bcb import http, sgs

async def main():
    try:
        results = await asyncio.gather(
            sgs.async_get(1),  # SELIC
            sgs.async_get(433),  # IPCA
        )
        return results
    finally:
        await http.aclose_async_client()

asyncio.run(main())
```

### P: Como trato erros e dados faltantes?
**R:** A biblioteca lança exceções específicas:
- `CurrencyNotFoundError`: Símbolo de moeda não encontrado
- `SGSError`: Erro do serviço SGS
- `BCBRateLimitError`: Limite de requisições excedido (HTTP 429)
- `BCBAPIError`: Outros erros de API

```python
from bcb import sgs
from bcb.exceptions import SGSError, BCBRateLimitError

try:
    df = sgs.get(99999)  # Código inválido
except SGSError as e:
    print(f"Erro de dados: {e}")
except BCBRateLimitError:
    print("Limite de requisições excedido - tente novamente mais tarde")
```

### P: Como habilito logging para depurar requisições?
**R:** A biblioteca usa o módulo logging padrão do Python:
```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("bcb")
logger.setLevel(logging.DEBUG)

# Agora todas as requisições/respostas HTTP serão registradas
```

### P: Existe cache para evitar requisições redundantes?
**R:** Sim:
- `bcb.currency`: Cache em memória automático de listas de moedas
- `bcb.odata`: Metadados OData em cache por URL de serviço
- Chame `currency.clear_cache()` para resetar se dados mudarem

### P: Posso usar isso em uma aplicação de longa duração?
**R:** Sim, mas tenha cuidado com:
- Limites de requisições: APIs BCB podem ter limites; implemente backoff se necessário
- Cache: Cache de moedas persiste em memória; limpe se atualizações de dados importarem
- Pool de conexões: Usa httpx com connection pooling por padrão
- API Assíncrona: use métodos async para comportamento verdadeiramente não-bloqueante e chame `await bcb.http.aclose_async_client()` no encerramento de aplicações assíncronas longas

### P: Como contribuo ou reporto problemas?
**R:** Visite o [repositório GitHub](https://github.com/wilsonfreitas/python-bcb) para:
- Reportar bugs
- Solicitar features
- Enviar pull requests
- Ver documentação

### P: Como gero a documentação localmente?
**R:** As dependências de documentação ficam no grupo `docs` do `uv`:
```shell
uv run --group docs sphinx-build -b html docs docs/_build/html
```

A saída HTML é gerada em `docs/_build/html`. Edite os arquivos fonte em `docs/`; não edite os arquivos gerados em `docs/_build`.

### P: Onde encontro documentação mais detalhada?
**R:**
- [Documentação de API](https://wilsonfreitas.github.io/python-bcb/)
- [Diretório de Exemplos](./examples/)
- Docstrings inline: `help(bcb.sgs.get)`, `help(bcb.currency.get)`, etc.
- [Portal de Dados Abertos BCB](https://dadosabertos.bcb.gov.br/)
