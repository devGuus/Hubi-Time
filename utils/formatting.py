"""Formatacao de duracoes de tempo para exibicao ('08h34')."""
from __future__ import annotations

from datetime import time


def format_minutes_as_hours(total_minutes: int, show_sign: bool = False) -> str:
    """Converte minutos totais em string 'HHhMM'. Negativos ficam '-HHhMM'."""
    sign = ""
    if total_minutes < 0:
        sign = "-"
        total_minutes = abs(total_minutes)
    elif show_sign and total_minutes > 0:
        sign = "+"

    hours, minutes = divmod(total_minutes, 60)
    return f"{sign}{hours:02d}h{minutes:02d}"


def format_time_or_placeholder(value: time | None) -> str:
    if value is None:
        return "--:--"
    return value.strftime("%H:%M")


def minutes_to_decimal_hours(total_minutes: int) -> float:
    return round(total_minutes / 60.0, 2)
