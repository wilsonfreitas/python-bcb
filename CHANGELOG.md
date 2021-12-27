
# Changelog

## [0.1.4] - 2021-12-27
- Changed arguments start_date and end_date to start and end to bring conformity with commom python data libraries like Quandl and pandas-datareader, for example.

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