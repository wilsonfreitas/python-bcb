**bcb** is an interface to structure the information provided by the [Brazilian Central Bank](https://www.bcb.gov.br).
This package interfaces the [Brazilian Central Bank web services](https://www3.bcb.gov.br/sgspub) to provide data already formatted into pandas's data structures and download currency data from [Brazilian Centra Bank](https://www.bcb.gov.br) web site.

## Install

**bcb** is avalilable at PyPI, so it is pip instalable.

	pip install python-bcb

## Using

Getting currency rates data.

```python
from bcb  import currency
from datetime import date

currency.get('USD', start_date=date(2020, 12, 1), end_date=date(2020, 12, 31))
```

The rates are quoted in BRL.


