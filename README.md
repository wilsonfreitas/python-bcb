# python-bcb

**python-bcb** é uma interface em Python estruturada para obter informações
da API de dados abertos do [Banco Central do Brasil](https://www.bcb.gov.br).

[![Downloads](https://img.shields.io/pypi/dm/python-bcb.svg)](https://pypi.python.org/pypi/python-bcb/)
[![image](https://img.shields.io/pypi/v/python-bcb.svg?color=green)](https://pypi.python.org/pypi/python-bcb/)
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
