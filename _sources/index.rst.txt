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
   Veja a documentação em :ref:`SGS`.
``Conversor de Moedas``
   Implementado no módulo ``currency``, um conjunto de funções que realiza webscraping
   no site do `Conversor de Moedas <https://www.bcb.gov.br/conversao>`_
   do Banco Central, possível obter séries temporais de frequência diária
   de diversas moedas.
   Veja a documentação em :ref:`Conversor de Moedas`.
``Moedas OData``
   O Banco Central disponibiliza diversas informações em APIs que
   seguem o padrão `OData <https://odata.org>`.
   A classe :py:class:`bcb.PTAX` implementa uma API OData que
   entrega os boletins diários de taxas de câmbio do Banco Central.
   Esta API entrega mais informações do que o que é obtido no
   ``Conversor de Moedas``.
   Veja a documentação em :ref:`API de Moedas`.
``Expectativas``
   A API de Expectativas de Mercado traz todas as estatísticas das variáveis
   macroeconômicas fornecidos por um conjuto de instituições do mercado
   financeiro.
   A classe :py:class:`bcb.Expectativas` implementa essa interface no
   padrão OData.
   Veja a documentação em :ref:`API de Expectativas`.
``Taxas de Juros``
   API que retorna as taxas de juros de operações de crédito por instituição financeira (médias dos últimos 5 dias).
   A classe :py:class:`bcb.TaxaJuros` implementa essa interface.
   Veja a documentação em :ref:`Taxas de Juros`.
``ODataAPI``
   O BCB disponibiliza diversas APIs que seguem a especificação OData.
   Algumas APIs mais utilizadas como as :py:class:`bcb.PTAX` e
   :py:class:`bcb.Expectativas` possuem uma classe específica, para as
   APIs menos utilizadas, é possível utilizar a classe :py:class:`bcb.ODataAPI`
   para acessar a API.
   Toda API que segue a especificação OData possui uma URL de acesso, esta URL
   é passada para a classe :py:class:`bcb.ODataAPI` e o objeto criado dá
   total acesso a API.
   Veja a documentação em :ref:`Classe ODataAPI`.
Muito mais
   Veja todos os *endpoints* implementados na documentação de nossa :ref:`API`.


Uso
===

.. ipython:: python

   from bcb import sgs
   sgs.get(('IPCA', 433), last=12)


.. toctree::
   :maxdepth: 1

   sgs
   currency
   expectativas
   taxajuros
   odata
   api

Índices e tabelas
==================

* :ref:`genindex`
* :ref:`modindex`