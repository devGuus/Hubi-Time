"""Validacoes de formulario e deteccao de inconsistencias de horario."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import time

from config.constants import MIN_PASSWORD_LENGTH

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email.strip()))


@dataclass
class PasswordValidationResult:
    is_valid: bool
    errors: list[str]


def validate_password(password: str) -> PasswordValidationResult:
    errors = []
    if len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f"A senha deve ter no minimo {MIN_PASSWORD_LENGTH} caracteres.")
    if not any(c.isupper() for c in password):
        errors.append("A senha deve conter ao menos uma letra maiuscula.")
    if not any(c.isdigit() for c in password):
        errors.append("A senha deve conter ao menos um numero.")
    return PasswordValidationResult(is_valid=not errors, errors=errors)


def passwords_match(password: str, confirmation: str) -> bool:
    return password == confirmation and len(password) > 0


@dataclass
class TimeInconsistencyWarning:
    field: str
    message: str


def detect_time_inconsistencies(
    entry_time: time | None,
    lunch_start: time | None,
    lunch_end: time | None,
    exit_time: time | None,
) -> list[TimeInconsistencyWarning]:
    """Detecta situacoes suspeitas nos horarios informados. Nao bloqueia o
    salvamento - apenas sinaliza para o usuario decidir se corrige.
    """
    warnings: list[TimeInconsistencyWarning] = []

    if entry_time and lunch_start and lunch_start < entry_time:
        warnings.append(
            TimeInconsistencyWarning(
                "lunch_start", "A saida para o almoco e anterior ao horario de entrada."
            )
        )
    if lunch_start and lunch_end and lunch_end < lunch_start:
        warnings.append(
            TimeInconsistencyWarning(
                "lunch_end", "O retorno do almoco e anterior a saida para o almoco."
            )
        )
    if lunch_end and exit_time and exit_time < lunch_end:
        warnings.append(
            TimeInconsistencyWarning("exit_time", "A saida e anterior ao retorno do almoco.")
        )
    if entry_time and exit_time and not lunch_start and not lunch_end and exit_time < entry_time:
        warnings.append(
            TimeInconsistencyWarning("exit_time", "A saida e anterior ao horario de entrada.")
        )
    if entry_time and lunch_start and lunch_end and exit_time:
        total_minutes = (
            _to_minutes(exit_time)
            - _to_minutes(entry_time)
            - (_to_minutes(lunch_end) - _to_minutes(lunch_start))
        )
        if total_minutes > 16 * 60:
            warnings.append(
                TimeInconsistencyWarning(
                    "exit_time", "O total de horas trabalhadas no dia parece incomum (acima de 16h)."
                )
            )
    return warnings


def _to_minutes(t: time) -> int:
    return t.hour * 60 + t.minute
