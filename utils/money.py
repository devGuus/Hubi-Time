"""Utilidades monetarias. Sempre Decimal - nunca float - para valores sensiveis."""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENTS = Decimal("0.01")


def format_brl(value: Decimal | None) -> str:
    """Formata um Decimal como 'R$ 1.234,56'."""
    if value is None:
        return "R$ 0,00"
    quantized = value.quantize(CENTS, rounding=ROUND_HALF_UP)
    negative = quantized < 0
    quantized = abs(quantized)
    integer_part, decimal_part = f"{quantized:.2f}".split(".")

    grouped = []
    while len(integer_part) > 3:
        grouped.insert(0, integer_part[-3:])
        integer_part = integer_part[:-3]
    grouped.insert(0, integer_part)
    formatted = ".".join(grouped)

    sign = "-" if negative else ""
    return f"{sign}R$ {formatted},{decimal_part}"


def parse_brl(text: str) -> Decimal:
    """Converte texto como '1.234,56' ou '1234.56' para Decimal."""
    cleaned = text.strip().replace("R$", "").strip()
    if not cleaned:
        return Decimal("0")
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"Valor monetario invalido: {text}") from exc


def round_currency(value: Decimal) -> Decimal:
    return value.quantize(CENTS, rounding=ROUND_HALF_UP)
