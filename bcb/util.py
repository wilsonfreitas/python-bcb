
from datetime import datetime


class Date:
    def __init__(self, d=None, format='%Y-%m-%d'):
        d = d if d else date.today()
        if isinstance(d, str):
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
