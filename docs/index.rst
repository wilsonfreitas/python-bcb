.. python-bcb documentation master file, created by
   sphinx-quickstart on Mon Dec 27 10:36:49 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

python-bcb 
==========

.. toctree::
   :maxdepth: 1
   :caption: Conteúdo:

   sgs
   currency
   expectativas
   taxajuros
   odata
   api

**python-bcb** é uma interface em Python estruturada para obter informações
da API de dados abertos do `Banco Central do Brasil <https://www.bcb.gov.br>`_.

.. image:: _static/images/ipca12m-acumulado.png

O projeto de `Dados Abertos do Banco Central do Brasil <https://dadosabertos.bcb.gov.br/>`_
disponibiliza diversas APIs provendo acesso direto a dados de:

* Moedas
* Taxas de Juros
* Índices de preços
* Informações de Instituições Financeiras
* Expectativas do Mercado (Expectativas do Boletim FOCUS)
* E muito outros ...

O pacote ``python-bcb`` implementa interfaces para algumas APIs
disponibilizadas pelo Banco Central de forma que o resultado
das consultas, na maioria dos casos, é um ``DataFrame`` pandas
formatado com os dados.

Instalação
==========

**python-bcb** está disponível no `Python Package Index <https://pypi.org/project/python-bcb/>`_ e pode ser instalado via ``pip`` usando.

.. code-block:: bash

   pip install python-bcb


APIs implementadas
==================

``sgs``
   Utiliza o webservice do SGS
   (`Sistema Gerenciador de Séries Temporais <https://www3.bcb.gov.br/sgspub/>`_)
   para obter os dados.
   Diversas séries estão disponíveis no SGS: taxas de juros, índices de preços,
   indicadores econômicos, ..., e com um simples chamado da função
   :py:func:`bcb.sgs.get` é possível tê-las
   em um ``DataFrame`` pandas.
``Conversor de Moedas``
   Implementado no módulo ``currency``, um conjunto de funções que realiza webscraping
   no site do `Conversos de Moedas <https://www.bcb.gov.br/conversao>`_
   do Banco Central, possível obter séries temporais de frequência diária
   de diversas moedas.
``Moedas OData``
   O Banco Central disponibiliza diversas informações em APIs que
   seguem o padrão `OData <https://odata.org>`.
   A classe :py:class:`bcb.PTAX` implementa uma API OData que
   entrega os boletins diários de taxas de câmbio do Banco Central.
   Esta API entrega mais informações do que o que é obtido no
   ``Conversor de Moedas``.
``Expectativas``
   A API de Expectativas de Mercado traz todas as estatísticas das variáveis
   macroeconômicas fornecidos por um conjuto de instituições do mercado
   financeiro.
   A classe :py:class:`bcb.Expectativas` implementa essa interface no
   padrão OData.


Uso
===

.. ipython:: python

   from bcb import sgs
   sgs.get(('IPCA', 433), last=12)


Índices e tabelas
==================

* :ref:`genindex`
* :ref:`modindex`