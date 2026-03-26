"""
Example: Querying OData APIs

This example demonstrates how to use the OData client to query
the Central Bank's OData endpoints with filters and sorting.
"""

from bcb import Expectativas

# Create an API instance for market expectations
api = Expectativas()

# Get the entity set for annual market expectations
endpoint = api.get_endpoint("ExpectativasMercadoAnuais")

# Example 1: Simple query with limit
print("Example 1: Get first 5 records")
df = endpoint.get(limit=5)
print(df)
print()

# Example 2: Query with filter - get specific indicator
print("Example 2: Filter by indicator (IPCA)")
query = endpoint.query().filter(endpoint.Indicador == "IPCA").limit(10)
df = query.collect()
print(df)
print()

# Example 3: Multiple filters (AND condition)
print("Example 3: Multiple filters")
query = (
    endpoint.query()
    .filter(endpoint.Indicador == "IPCA")
    .filter(endpoint.Mediana > 3.0)
    .limit(10)
)
df = query.collect()
print(df)
print()

# Example 4: Using comparison operators
print("Example 4: Range filters")
query = (
    endpoint.query()
    .filter((endpoint.Mediana >= 3.0) & (endpoint.Mediana <= 5.0))
    .limit(5)
)
# Note: AND (&) operator usage with OData filters
try:
    df = query.collect()
    print(df)
except Exception as e:
    print(f"Note: Complex filters may need different syntax. {type(e).__name__}")
print()

# Example 5: Ordering results
print("Example 5: Order by descending")
query = endpoint.query().orderby(endpoint.Mediana.desc()).limit(5)
df = query.collect()
print(df)
print()

# Example 6: Select specific columns
print("Example 6: Select specific columns")
query = endpoint.query().select([endpoint.Indicador, endpoint.Mediana]).limit(5)
df = query.collect()
print(df)
print()

# Example 7: Get raw JSON
print("Example 7: Raw JSON output")
query = endpoint.query().limit(2)
json_str = query.collect(output="text")
print(json_str[:300])
print()

# Example 8: Using chainable API
print("Example 8: Chained query")
df = (
    endpoint.query()
    .filter(endpoint.Indicador == "PIB")
    .orderby(endpoint.Data.desc())
    .limit(3)
    .collect()
)
print(df)
