.. _async:

APIs Assíncronas
================

O **python-bcb** oferece suporte completo a programação assíncrona através de métodos ``async_get()`` e ``async_collect()`` em todos os módulos.
Isso permite buscar dados de forma não-bloqueante e executar múltiplas requisições concorrentemente usando ``asyncio``.

Quando Usar APIs Assíncronas
----------------------------

Use as APIs assíncronas quando você precisa:

* **Buscar múltiplas séries** — Reduz o tempo total de execução
* **Integrar com código assíncrono** — Evita bloquear a event loop
* **Processamento em larga escala** — Milhares de requisições sem I/O bloqueante
* **Aplicações web/CLI** — Melhor responsividade e throughput

Exemplo Básico: Múltiplas Séries SGS
------------------------------------

Buscar vários indicadores SGS concorrentemente é muito mais rápido que fazer requisições sequenciais:

.. code-block:: python

    import asyncio
    from bcb import sgs

    async def fetch_economic_indicators():
        """Buscar SELIC, CDI e IPCA concorrentemente."""
        # Criar tasks para requisições concorrentes
        results = await asyncio.gather(
            sgs.async_get(1, start='2024-01-01'),      # SELIC
            sgs.async_get(12, start='2024-01-01'),     # CDI
            sgs.async_get(433, start='2024-01-01'),    # IPCA
        )

        selic_df, cdi_df, ipca_df = results
        return selic_df, cdi_df, ipca_df

    # Executar
    selic, cdi, ipca = asyncio.run(fetch_economic_indicators())
    print(selic.head())

Módulo SGS: async_get()
-----------------------

A função :py:func:`bcb.sgs.async_get` é a versão assíncrona de :py:func:`bcb.sgs.get`.
Busca dados de múltiplos códigos SGS concorrentemente com a mesma interface que a versão síncrona.

**Exemplo com múltiplos códigos:**

.. code-block:: python

    import asyncio
    from bcb import sgs

    async def main():
        # Buscar vários indicadores de uma vez
        df = await sgs.async_get(
            [1, 11, 12, 433],  # SELIC, Taxa Over, CDI, IPCA
            start='2023-01-01',
            end='2024-12-31'
        )
        print(df.head())

    asyncio.run(main())

Módulo Currency: async_get()
-----------------------------

A função :py:func:`bcb.currency.async_get` é a versão assíncrona de :py:func:`bcb.currency.get`.
Busca taxas de câmbio de forma assíncrona com a mesma interface que a versão síncrona.

**Exemplo:**

.. code-block:: python

    import asyncio
    from bcb import currency

    async def main():
        # Buscar taxas de câmbio
        usd = await currency.async_get('USD', start='2024-01-01', end='2024-12-31')
        print(usd.head())

    asyncio.run(main())

OData: async_collect()
----------------------

Todas as queries OData suportam métodos assíncronos para execução não-bloqueante:

* :py:meth:`ODataQuery.async_collect` — versão assíncrona de :py:meth:`ODataQuery.collect`
* :py:meth:`Endpoint.async_get` — versão assíncrona de :py:meth:`Endpoint.get`
* :py:meth:`Endpoint.async_query` — retorna uma query pronta para execução assíncrona

**Exemplo com Expectativas:**

.. code-block:: python

    import asyncio
    from bcb import Expectativas

    async def main():
        api = Expectativas()
        endpoint = api.get_endpoint('ExpectativasMercadoAnuais')

        # Construir query e executar de forma assíncrona
        df = await (
            endpoint.query()
            .filter(endpoint.Indicador == 'IPCA')
            .limit(100)
            .async_collect()
        )
        print(df)

    asyncio.run(main())

Padrão asyncio.gather() — Operações Paralelas
----------------------------------------------

Use ``asyncio.gather()`` para executar várias operações em paralelo:

.. code-block:: python

    import asyncio
    from bcb import sgs, currency
    from bcb import Expectativas

    async def main():
        # Executar 3 operações em paralelo
        selic_task = sgs.async_get(1, start='2024-01-01')
        usd_task = currency.async_get('USD', start='2024-01-01')

        api = Expectativas()
        endpoint = api.get_endpoint('ExpectativasMercadoAnuais')
        expectations_task = endpoint.query().filter(
            endpoint.Indicador == 'IPCA'
        ).limit(10).async_collect()

        # Aguardar todas as operações
        selic, usd, expectations = await asyncio.gather(
            selic_task,
            usd_task,
            expectations_task
        )

        return selic, usd, expectations

    selic, usd, expectations = asyncio.run(main())

Tratamento de Erros
-------------------

As APIs assíncronas lançam as mesmas exceções que as síncronas:

.. code-block:: python

    import asyncio
    from bcb import sgs
    from bcb.exceptions import SGSError, BCBRateLimitError

    async def main():
        try:
            df = await sgs.async_get(99999)  # Código inválido
        except SGSError as e:
            print(f"Erro de dados SGS: {e}")
        except BCBRateLimitError:
            print("Limite de requisições excedido - tente novamente mais tarde")

    asyncio.run(main())

Performance: Síncrono vs Assíncrono
-----------------------------------

**Requisições Sequenciais (bloqueante):**

.. code-block:: python

    # Leva ~5 segundos (1s + 1s + 1s + cada requisição é bloqueante)
    df1 = sgs.get(1, start='2024-01-01')
    df2 = sgs.get(11, start='2024-01-01')
    df3 = sgs.get(12, start='2024-01-01')

**Requisições Concorrentes (assíncrono):**

.. code-block:: python

    # Leva ~1 segundo (todas 3 são executadas em paralelo)
    import asyncio

    async def main():
        df1, df2, df3 = await asyncio.gather(
            sgs.async_get(1, start='2024-01-01'),
            sgs.async_get(11, start='2024-01-01'),
            sgs.async_get(12, start='2024-01-01'),
        )

    asyncio.run(main())

Limpeza de Recursos
-------------------

Para aplicações de longa duração, feche o cliente assíncrono quando terminar:

.. code-block:: python

    import asyncio
    from bcb import http

    async def main():
        # ... suas operações assíncronas ...
        pass

    asyncio.run(main())

    # Fechar cliente assíncrono
    asyncio.run(http.close_async_client())

Limitações
----------

* **Concorrência sem limite** — Use um ``asyncio.Semaphore()`` para limitar requisições simultâneas
* **Rate limiting** — APIs BCB podem ter limites; implemente backoff exponencial se necessário
* **Ciclos de evento** — APIs assíncronas exigem uma event loop ativa (use ``asyncio.run()``)

**Exemplo com Semaphore:**

.. code-block:: python

    import asyncio
    from bcb import sgs

    async def main():
        # Limitar a 3 requisições simultâneas
        semaphore = asyncio.Semaphore(3)

        async def fetch_with_limit(code):
            async with semaphore:
                return await sgs.async_get(code, start='2024-01-01')

        codes = [1, 11, 12, 433, 189]
        results = await asyncio.gather(*[fetch_with_limit(c) for c in codes])

        return results

    asyncio.run(main())

Veja Também
-----------

* :ref:`SGS` — Documentação completa do módulo SGS
* :ref:`Conversor de Moedas` — Documentação do módulo currency
* :ref:`OData` — Documentação do cliente OData
* `asyncio — asyncpython <https://docs.python.org/3/library/asyncio.html>`_
