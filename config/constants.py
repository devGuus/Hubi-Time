"""Constantes e enumeracoes compartilhadas pela aplicacao."""
from __future__ import annotations

from enum import Enum


class DayType(str, Enum):
    """Tipo de dia associado a um registro de jornada."""

    NORMAL = "normal"
    FOLGA = "folga"
    FERIAS = "ferias"
    FERIADO = "feriado"
    ATESTADO = "atestado"
    AUSENCIA = "ausencia"
    OUTRO = "outro"

    @property
    def label_pt(self) -> str:
        return {
            DayType.NORMAL: "Dia normal",
            DayType.FOLGA: "Folga",
            DayType.FERIAS: "Ferias",
            DayType.FERIADO: "Feriado",
            DayType.ATESTADO: "Atestado",
            DayType.AUSENCIA: "Ausencia",
            DayType.OUTRO: "Outro",
        }[self]

    @property
    def counts_as_expected_workday(self) -> bool:
        """Se True, a carga horaria prevista do dia deve ser cobrada normalmente."""
        return self == DayType.NORMAL


class RecordStatus(str, Enum):
    """Status de um registro de jornada (soft delete)."""

    ACTIVE = "active"
    ARCHIVED = "archived"


class HistoryAction(str, Enum):
    """Acao registrada no historico de auditoria de um registro de jornada."""

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    ARCHIVE = "ARCHIVE"
    RESTORE = "RESTORE"


class NotificationType(str, Enum):
    """Tipos de notificacao/alerta exibidos na aplicacao."""

    MISSING_LUNCH_RETURN = "missing_lunch_return"
    INCOMPLETE_TODAY = "incomplete_today"
    TIME_INCONSISTENCY = "time_inconsistency"
    INCOMPLETE_MONTH = "incomplete_month"
    GENERIC = "generic"


class Theme(str, Enum):
    LIGHT = "light"
    DARK = "dark"


class Weekday(int, Enum):
    """Dias da semana alinhados ao Python (Monday=0)."""

    SEGUNDA = 0
    TERCA = 1
    QUARTA = 2
    QUINTA = 3
    SEXTA = 4
    SABADO = 5
    DOMINGO = 6

    @property
    def label_pt(self) -> str:
        return {
            Weekday.SEGUNDA: "Segunda-feira",
            Weekday.TERCA: "Terca-feira",
            Weekday.QUARTA: "Quarta-feira",
            Weekday.QUINTA: "Quinta-feira",
            Weekday.SEXTA: "Sexta-feira",
            Weekday.SABADO: "Sabado",
            Weekday.DOMINGO: "Domingo",
        }[self]


WORK_RECORD_TIME_FIELDS: tuple[str, ...] = (
    "entry_time",
    "lunch_start",
    "lunch_end",
    "exit_time",
)

# Campos do work_record rastreados no historico de auditoria.
WORK_RECORD_AUDITED_FIELDS: tuple[str, ...] = (
    *WORK_RECORD_TIME_FIELDS,
    "day_type",
    "notes",
    "status",
)

DEFAULT_WEEKLY_HOURS: dict[str, float] = {
    "segunda": 8.0,
    "terca": 8.0,
    "quarta": 8.0,
    "quinta": 8.0,
    "sexta": 8.0,
    "sabado": 0.0,
    "domingo": 0.0,
}

DEFAULT_MONTHLY_HOURS = 220.0

MIN_PASSWORD_LENGTH = 8
# Comprimento do codigo OTP enviado por e-mail pelo Supabase Auth. Nao e um
# padrao fixo do GoTrue - confirme o valor real recebido no e-mail do seu
# projeto (Authentication > Email Templates > {{ .Token }}) e ajuste aqui
# se for diferente.
OTP_CODE_LENGTH = 8
SESSION_KEYRING_KEY = "supabase_refresh_token"
SESSION_KEYRING_EMAIL_KEY = "supabase_last_email"

DATE_FORMAT_DISPLAY = "dd/MM/yyyy"
TIME_FORMAT_DISPLAY = "HH:mm"
