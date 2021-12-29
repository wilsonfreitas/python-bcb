.. python-bcb documentation master file, created by
   sphinx-quickstart on Mon Dec 27 10:36:49 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

python-bcb 
==========

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


Instalação
==========

**python-bcb** está disponível no `Python Package Index <https://pypi.org/project/python-bcb/>`_ e pode ser instalado via ``pip`` usando.

.. code-block:: bash

   pip install python-bcb


Módulos
=======

``sgs``
   Utiliza o webservice do SGS
   (`Sistema Gerenciador de Séries Temporais <https://www3.bcb.gov.br/sgspub/>`_).
   Diversas séries estão disponíveis no SGS: taxas de juros, índices de preços,
   indicadores econômicos, ....

``currency``
   Implementado no módulo ``currency`` que obtem dados de séries temporais de moedas do site
   <https://www.bcb.gov.br/conversao> via webscraping.


Uso
===

.. ipython:: python

   from bcb import sgs
   sgs.get(('IPCA', 433), last=12)



.. toctree::
   :maxdepth: 2
   :caption: Conteúdo:

   sgs.md
   currency.rst
   api.rst


Índices e tabelas
==================

* :ref:`genindex`
* :ref:`modindex`