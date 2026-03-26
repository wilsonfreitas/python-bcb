"""
Exemplo: Usando APIs Assíncronas

Este exemplo demonstra como usar as versões assíncronas das APIs
para busca de dados concorrente (útil para buscar múltiplas séries).
"""

import asyncio
from datetime import datetime
from bcb import sgs, currency
from bcb.odata.api import Expectativas


async def fetch_multiple_sgs_series():
    """Buscar múltiplas séries temporais do SGS concorrentemente."""
    print("Exemplo 1: Buscando múltiplas séries do SGS concorrentemente")

    # Buscar SELIC, CDI e IPCA concorrentemente
    codes = [1, 12, 433]  # SELIC, CDI, IPCA

    df = await sgs.async_get(codes, start="2023-01-01", end="2024-12-31", multi=True)
    print("Busca concorrente do SGS concluída")
    print(df.head())
    print()


async def fetch_multiple_currencies():
    """Buscar taxas de câmbio concorrentemente."""
    print("Exemplo 2: Buscando taxas de câmbio concorrentemente")

    # Buscar taxa do USD (nota: você precisaria implementar async multi-símbolo
    # para isso ser verdadeiramente concorrente para diferentes símbolos)
    df = await currency.async_get("USD", start="2024-01-01", end="2024-12-31")
    print("Busca de câmbio assíncrona concluída")
    print(df.head())
    print()


async def fetch_odata_async():
    """Buscar resultados OData de forma assíncrona."""
    print("Exemplo 3: Buscando resultados OData de forma assíncrona")

    api = Expectativas()
    endpoint = api.get_endpoint("ExpectativasMercadoAnuais")

    # Construir e executar consulta de forma assíncrona
    query = endpoint.query().filter(endpoint.Indicador == "IPCA").limit(5)
    df = await query.async_collect()
    print("Busca OData assíncrona concluída")
    print(df)
    print()


async def concurrent_operations():
    """Executar múltiplas operações assíncronas concorrentemente."""
    print("Exemplo 4: Múltiplas operações concorrentes")

    # Criar tarefas para execução concorrente
    tasks = [
        sgs.async_get(1, start="2024-01-01", end="2024-12-31"),  # SELIC
        sgs.async_get(11, start="2024-01-01", end="2024-12-31"),  # CDI
        sgs.async_get(433, start="2024-01-01", end="2024-12-31"),  # IPCA
    ]

    # Aguardar conclusão de todas as tarefas
    results = await asyncio.gather(*tasks)
    print(f"Buscadas {len(results)} séries concorrentes")
    print("Amostra da primeira série:")
    print(results[0].head())
    print()


async def main():
    """Executar todos os exemplos assíncronos."""
    try:
        await fetch_multiple_sgs_series()
        await fetch_multiple_currencies()
        await fetch_odata_async()
        await concurrent_operations()
    except Exception as e:
        print(f"Erro: {type(e).__name__}: {e}")


if __name__ == "__main__":
    # Executar os exemplos assíncronos
    # Nota: Isso requer Python 3.7+ com asyncio
    asyncio.run(main())
