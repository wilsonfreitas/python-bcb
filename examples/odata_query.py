"""
Exemplo: Consultando APIs OData

Este exemplo demonstra como usar o cliente OData para consultar
os endpoints OData do Banco Central com filtros e ordenação.
"""

from bcb import Expectativas

# Criar uma instância de API para expectativas de mercado
api = Expectativas()

# Obter o conjunto de entidades para expectativas de mercado anual
endpoint = api.get_endpoint("ExpectativasMercadoAnuais")

# Exemplo 1: Consulta simples com limite
print("Exemplo 1: Obter os primeiros 5 registros")
df = endpoint.get(limit=5)
print(df)
print()

# Exemplo 2: Consulta com filtro - obter indicador específico
print("Exemplo 2: Filtrar por indicador (IPCA)")
query = endpoint.query().filter(endpoint.Indicador == "IPCA").limit(10)
df = query.collect()
print(df)
print()

# Exemplo 3: Múltiplos filtros (condição AND)
print("Exemplo 3: Múltiplos filtros")
query = (
    endpoint.query()
    .filter(endpoint.Indicador == "IPCA")
    .filter(endpoint.Mediana > 3.0)
    .limit(10)
)
df = query.collect()
print(df)
print()

# Exemplo 4: Usando múltiplos filtros para intervalo
print("Exemplo 4: Filtros de intervalo")
query = (
    endpoint.query()
    .filter(endpoint.Mediana >= 3.0)
    .filter(endpoint.Mediana <= 5.0)
    .limit(5)
)
try:
    df = query.collect()
    print(df)
except Exception as e:
    print(f"Nota: Filtros podem ter limitações. {type(e).__name__}: {e}")
print()

# Exemplo 5: Ordenar resultados
print("Exemplo 5: Ordenar por decrescente")
query = endpoint.query().orderby(endpoint.Mediana.desc()).limit(5)
df = query.collect()
print(df)
print()

# Exemplo 6: Selecionar colunas específicas
print("Exemplo 6: Selecionar colunas específicas")
query = endpoint.query().select(endpoint.Indicador, endpoint.Mediana).limit(5)
df = query.collect()
print(df)
print()

# Exemplo 7: Obter saída JSON bruta
print("Exemplo 7: Saída JSON bruta")
query = endpoint.query().limit(2)
json_str = query.collect(output="text")
print(json_str[:300])
print()

# Exemplo 8: Usando API encadeável
print("Exemplo 8: Consulta encadeada")
df = (
    endpoint.query()
    .filter(endpoint.Indicador == "PIB")
    .orderby(endpoint.Data.desc())
    .limit(3)
    .collect()
)
print(df)
