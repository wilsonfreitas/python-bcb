"""
Exemplo: Buscando Taxas de Câmbio

Este exemplo demonstra como buscar dados de taxa de câmbio do
sistema PTAX do Banco Central (cotações diárias de câmbio).
"""

import datetime as dt

from bcb import currency

# Buscar uma única moeda (USD)
# Retorna tanto taxas de compra quanto venda
usd_rates = currency.get("USD", start="2024-01-01", end="2024-12-31")
print("Taxas de Câmbio do USD")
print(usd_rates.head())
print()

# Obter apenas preços de venda (ask)
usd_ask = currency.get("USD", start="2024-01-01", end="2024-12-31", side="ask")
print("Apenas Preços de Venda do USD")
print(usd_ask.head())
print()

# Obter apenas preços de compra (bid)
usd_bid = currency.get("USD", start="2024-01-01", end="2024-12-31", side="bid")
print("Apenas Preços de Compra do USD")
print(usd_bid.head())
print()

# Buscar múltiplas moedas de uma vez
symbols = ["USD", "EUR"]
try:
    rates = currency.get(symbols, start="2024-01-01", end="2024-12-31")
    print("Múltiplas Moedas (USD + EUR)")
    print(rates.head())
except Exception as e:
    print(f"Nota: Algumas moedas podem não estar disponíveis. Erro: {e}")
print()

# Obter dados agrupados por lado em vez de símbolo
try:
    rates = currency.get(
        ["USD", "EUR"],
        start="2024-01-01",
        end="2024-12-31",
        side="both",
        groupby="side",
    )
    print("Moedas Agrupadas por Lado")
    print(rates.head())
except Exception as e:
    print(f"Nota: Erro ao buscar múltiplas moedas. Erro: {e}")
print()

# Obter texto CSV bruto em vez de DataFrame
csv_text = currency.get("USD", start="2024-01-01", end="2024-01-31", output="text")
print("Saída CSV bruto (primeiros 200 caracteres):")
print(csv_text[:200])
print()

# Limpar o cache se executando múltiplas requisições
currency.clear_cache()
print("Cache limpo para requisições frescas")

# Obter taxa de câmbio de hoje (aproximada)
today = dt.date.today()
today_rates = currency.get("USD", start=today - dt.timedelta(days=30), end=today)
print("\nTaxas de Câmbio Recentes do USD")
print(today_rates.tail(5))
