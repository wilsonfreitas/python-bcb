
# Changelog

## [0.1.5] - 2022-01-16
- Implemented the definetive wraper for OData APIs.
  - A few APIs have been unlocked: Expectativas, PTAX, taxaJuros, MercadoImobiliario, SPI
- Updated documentation

## [0.1.4] - 2021-12-27
- Changed arguments start_date and end_date to start and end to bring conformity with commom python data libraries like Quandl and pandas-datareader, for example.
- bcb.currency.get multi argument, which refers to multivariate time series returned (defaults to True)
- bcb.sgs.get groupby argument
- Sphinx docs implemented

## [0.1.3] - 2021-04-14
- BUG fix in get_valid_currency_list: recurrent ConnectionError
- Added side and group_by arguments to currency.get function
- New notebooks with examples
- Added join argument to sgs.get function

## [0.1.2] - 2021-01-25
- New sgs module downloads time series from SGS BACEN's site
- Notebooks created to show a few examples
- Date class moved to utils module

## [0.1.1] - 2021-01-16

- Bug fixes

## [0.1.0] - 2021-01-16

- First commit
- currency module downloads currency rates quoted in Brazilian Real (BRL)