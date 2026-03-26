"""
Exemplo: Buscando Dados de Séries Temporais do SGS

Este exemplo demonstra como buscar e trabalhar com dados de séries temporais
do SGS (Sistema Gerenciador de Séries Temporais) do Banco Central.
"""

import pandas as pd
from bcb import sgs

# Buscar uma única série temporal
# Taxa Selic (código 1)
selic = sgs.get(1, start="2020-01-01", end="2024-12-31")
print("Série Temporal da Taxa Selic")
print(selic.head())
print()

# Buscar os últimos 20 dias
ultimos_20_dias = sgs.get(1, last=20)
print("Últimos 20 dias da Selic")
print(ultimos_20_dias.tail(10))
print()

# Buscar múltiplas séries temporais de uma vez
# SELIC (1) e IPCA (433)
multi_series = sgs.get([("SELIC", 1), ("IPCA", 433)], start="2023-01-01", end="2024-12-31")
print("Múltiplas Séries Temporais (SELIC + IPCA)")
print(multi_series.head())
print()

# Obter respostas JSON bruto em vez de DataFrames
json_data = sgs.get(1, start="2024-01-01", end="2024-12-31", output="text")
print("Saída JSON bruto (primeiros 200 caracteres):")
print(json_data[:200])
print()

# Usar com pandas para análise
selic_df = sgs.get(1, start="2020-01-01", end="2024-12-31")
print("Estatísticas da Selic:")
print(selic_df.describe())
