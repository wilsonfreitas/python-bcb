from bcb import currency

df = currency.get(['USD', 'EUR'], start='2000-01-01',
                  end='2021-01-01', side='ask')
df.plot(figsize=(12, 6))
