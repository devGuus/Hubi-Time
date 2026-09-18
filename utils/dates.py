"""Utilidades de data/hora. Sem logica de negocio, apenas conversoes puras."""
from __future__ import annotations

import calendar
from datetime import date, timedelta

from config.constants import Weekday

WEEKDAY_LABELS_PT = {
    0: "Segunda-feira",
    1: "Terca-feira",
    2: "Quarta-feira",
    3: "Quinta-feira",
    4: "Sexta-feira",
    5: "Sabado",
    6: "Domingo",
}

MONTH_LABELS_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Marco", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}


def to_weekday(d: date) -> Weekday:
    return Weekday(d.weekday())


def weekday_label(d: date) -> str:
    return WEEKDAY_LABELS_PT[d.weekday()]


def month_label(month: int) -> str:
    return MONTH_LABELS_PT[month]


def format_date_br(d: date | None) -> str:
    if d is None:
        return "--/--/----"
    return d.strftime("%d/%m/%Y")


def parse_date_br(text: str) -> date:
    return date(
        year=int(text[6:10]),
        month=int(text[3:5]),
        day=int(text[0:2]),
    )


def month_range(year: int, month: int) -> tuple[date, date]:
    """Retorna (primeiro_dia, ultimo_dia) do mes."""
    first = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    last = date(year, month, last_day)
    return first, last


def week_range(d: date) -> tuple[date, date]:
    """Retorna (segunda, domingo) da semana que contem `d`."""
    start = d - timedelta(days=d.weekday())
    end = start + timedelta(days=6)
    return start, end


def year_range(year: int) -> tuple[date, date]:
    return date(year, 1, 1), date(year, 12, 31)


def iter_dates(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def add_months(d: date, months: int) -> date:
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)
