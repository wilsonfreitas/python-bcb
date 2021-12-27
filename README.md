# python-bcb

**python-bcb** é uma interface em Python estruturada para obter informações
da API de dados abertos do [Banco Central do Brasil](https://www.bcb.gov.br).

[![image](https://img.shields.io/pypi/v/python-bcb.svg)](https://pypi.python.org/pypi/python-bcb/)
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

# Módulos

`sgs`
:	Utiliza o webservice do SGS ([Sistema Gerenciador de Séries Temporais](https://www3.bcb.gov.br/sgspub/)). Diversas séries estão disponíveis no SGS: taxas de juros, índices de preços, indicadores econômicos, ....

`currency`
:	Implementado no módulo `currency` que obtem dados de séries temporais de moedas do site <https://www.bcb.gov.br/conversao> via webscraping.
