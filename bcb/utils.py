from datetime import date, datetime
from typing import TypeAlias, Union

BRAZILIAN_REGIONS = {
    "N": ["AC", "AP", "AM", "PA", "RO", "RR", "TO"],
    "NE": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
    "CO": ["DF", "GO", "MT", "MS"],
    "SE": ["ES", "MG", "RJ", "SP"],
    "S": ["PR", "RS", "SC"],
}
BRAZILIAN_STATES = []
for state in BRAZILIAN_REGIONS.values():
    BRAZILIAN_STATES.extend(state)

DateInput: TypeAlias = Union[str, datetime, "Date", date]


class Date:
    def __init__(self, d: DateInput, format: str = "%Y-%m-%d") -> None:
        if isinstance(d, str):
            if d == "now" or d == "today":
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
        self.date: date = d

    def format(self, fmts: str = "%Y-%m-%d") -> str:
        return datetime.strftime(self.date, fmts)

    def __gt__(self, other) -> bool:
        return self.date > other.date

    def __ge__(self, other) -> bool:
        return self.date >= other.date

    def __lt__(self, other) -> bool:
        return self.date < other.date

    def __le__(self, other) -> bool:
        return self.date <= other.date

    def __eq__(self, other) -> bool:
        return self.date == other.date

    def __repr__(self) -> str:
        return self.format()

    __str__ = __repr__
