"""
Example: Using Async APIs

This example demonstrates how to use the async versions of the APIs
for concurrent data fetching (useful for fetching multiple series).
"""

import asyncio
from datetime import datetime
from bcb import sgs, currency
from bcb.odata.api import Expectativas


async def fetch_multiple_sgs_series():
    """Fetch multiple SGS time series concurrently."""
    print("Example 1: Fetching multiple SGS series concurrently")

    # Fetch SELIC, CDI, and IPCA concurrently
    codes = [1, 12, 433]  # SELIC, CDI, IPCA

    df = await sgs.async_get(codes, start="2023-01-01", end="2024-12-31", multi=True)
    print("Concurrent SGS fetch completed")
    print(df.head())
    print()


async def fetch_multiple_currencies():
    """Fetch currency rates concurrently."""
    print("Example 2: Fetching currency rates concurrently")

    # Fetch USD rate (note: you'd need to implement multi-symbol async
    # for this to truly be concurrent for different symbols)
    df = await currency.async_get("USD", start="2024-01-01", end="2024-12-31")
    print("Async currency fetch completed")
    print(df.head())
    print()


async def fetch_odata_async():
    """Fetch OData results asynchronously."""
    print("Example 3: Fetching OData results asynchronously")

    api = Expectativas()
    endpoint = api.get_endpoint("ExpectativasMercadoAnuais")

    # Build and execute query asynchronously
    query = endpoint.query().filter(endpoint.Indicador == "IPCA").limit(5)
    df = await query.async_collect()
    print("Async OData fetch completed")
    print(df)
    print()


async def concurrent_operations():
    """Execute multiple async operations concurrently."""
    print("Example 4: Multiple concurrent operations")

    # Create tasks for concurrent execution
    tasks = [
        sgs.async_get(1, start="2024-01-01", end="2024-12-31"),  # SELIC
        sgs.async_get(11, start="2024-01-01", end="2024-12-31"),  # CDI
        sgs.async_get(433, start="2024-01-01", end="2024-12-31"),  # IPCA
    ]

    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks)
    print(f"Fetched {len(results)} concurrent series")
    print("First series sample:")
    print(results[0].head())
    print()


async def main():
    """Run all async examples."""
    try:
        await fetch_multiple_sgs_series()
        await fetch_multiple_currencies()
        await fetch_odata_async()
        await concurrent_operations()
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")


if __name__ == "__main__":
    # Run the async examples
    # Note: This requires Python 3.7+ with asyncio
    asyncio.run(main())
