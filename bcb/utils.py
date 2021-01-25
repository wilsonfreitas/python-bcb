
from datetime import datetime, date


class Date:
    def __init__(self, d=None, format='%Y-%m-%d', mindate=date(1900, 1, 1)):
        d = d if d else mindate
        if isinstance(d, str):
            if d == 'now' or d == 'today':
                d = date.today()
            else:
                d = datetime.strptime(d, format).date()
        elif isinstance(d, datetime):
            d = d.date()
        elif isinstance(d, Date):
            d = d.date
        elif isinstance(d, date):
            pass
        else:
            raise ValueError()
        self.date = d

    def format(self, fmts='%Y-%m-%d'):
        return datetime.strftime(self.date, fmts)

    def __gt__(self, other):
        return self.date > other.date

    def __ge__(self, other):
        return self.date >= other.date

    def __lt__(self, other):
        return self.date < other.date

    def __le__(self, other):
        return self.date <= other.date

    def __eq__(self, other):
        return self.date == other.date

    def __repr__(self):
        return self.format()

    __str__ = __repr__
