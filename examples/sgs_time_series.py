"""
Example: Fetching SGS Time Series Data

This example demonstrates how to fetch and work with time series data
from the Central Bank's SGS (Sistema Gerenciador de Séries Temporais).
"""

import pandas as pd
from bcb import sgs

# Fetch a single time series
# SELIC rate (code 1)
selic = sgs.get(1, start="2020-01-01", end="2024-12-31")
print("SELIC Rate Time Series")
print(selic.head())
print()

# Fetch the last 30 days
last_30_days = sgs.get(1, last=30)
print("Last 30 days of SELIC")
print(last_30_days.tail(10))
print()

# Fetch multiple time series at once
# SELIC (1) and IPCA (433)
codes = [
    ("SELIC", 1),
    ("IPCA", 433),
]
multi_series = sgs.get([("SELIC", 1), ("IPCA", 433)], start="2023-01-01", end="2024-12-31")
print("Multiple Time Series (SELIC + IPCA)")
print(multi_series.head())
print()

# Get raw JSON responses instead of DataFrames
json_data = sgs.get(1, start="2024-01-01", end="2024-12-31", output="text")
print("Raw JSON output (first 200 chars):")
print(json_data[:200])
print()

# Use with pandas for analysis
selic_df = sgs.get(1, start="2020-01-01", end="2024-12-31")
print("SELIC Statistics:")
print(selic_df.describe())
