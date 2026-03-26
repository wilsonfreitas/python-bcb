"""
Example: Fetching Currency Exchange Rates

This example demonstrates how to fetch exchange rate data from the
Central Bank's PTAX system (daily foreign exchange rates).
"""

from datetime import datetime
from bcb import currency

# Fetch a single currency (USD)
# Returns both bid and ask rates
usd_rates = currency.get("USD", start="2024-01-01", end="2024-12-31")
print("USD Exchange Rates")
print(usd_rates.head())
print()

# Get only ask prices
usd_ask = currency.get("USD", start="2024-01-01", end="2024-12-31", side="ask")
print("USD Ask Prices Only")
print(usd_ask.head())
print()

# Get only bid prices
usd_bid = currency.get("USD", start="2024-01-01", end="2024-12-31", side="bid")
print("USD Bid Prices Only")
print(usd_bid.head())
print()

# Fetch multiple currencies at once
symbols = ["USD", "EUR"]
try:
    rates = currency.get(symbols, start="2024-01-01", end="2024-12-31")
    print("Multiple Currencies (USD + EUR)")
    print(rates.head())
except Exception as e:
    print(f"Note: Some currencies may not be available. Error: {e}")
print()

# Get data grouped by side instead of symbol
try:
    rates = currency.get(
        ["USD", "EUR"],
        start="2024-01-01",
        end="2024-12-31",
        side="both",
        groupby="side",
    )
    print("Currencies Grouped by Side")
    print(rates.head())
except Exception as e:
    print(f"Note: Error fetching multiple currencies. Error: {e}")
print()

# Get raw CSV text instead of DataFrame
csv_text = currency.get("USD", start="2024-01-01", end="2024-01-31", output="text")
print("Raw CSV output (first 200 chars):")
print(csv_text[:200])
print()

# Clear the cache if running multiple requests
currency.clear_cache()
print("Cache cleared for fresh requests")

# Get today's USD rate (approximate)
import datetime as dt

today = dt.date.today()
today_rates = currency.get("USD", start=today - dt.timedelta(days=30), end=today)
print("\nRecent USD Rates")
print(today_rates.tail(5))
