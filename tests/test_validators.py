"""Testes de validacao: e-mail, senha e inconsistencias de horario."""
from __future__ import annotations

from datetime import time

from utils.validators import (
    detect_time_inconsistencies, is_valid_email, passwords_match, validate_password,
)


class TestEmailValidation:
    def test_valid_email(self):
        assert is_valid_email("usuario@empresa.com") is True

    def test_missing_at_sign_is_invalid(self):
        assert is_valid_email("usuario.empresa.com") is False

    def test_missing_domain_is_invalid(self):
        assert is_valid_email("usuario@") is False


class TestPasswordValidation:
    def test_strong_password_is_valid(self):
        result = validate_password("Senha1234")
        assert result.is_valid is True
        assert result.errors == []

    def test_short_password_is_invalid(self):
        result = validate_password("Ab1")
        assert result.is_valid is False

    def test_password_without_uppercase_is_invalid(self):
        result = validate_password("senha1234")
        assert any("maiuscula" in e for e in result.errors)

    def test_password_without_digit_is_invalid(self):
        result = validate_password("SenhaSegura")
        assert any("numero" in e for e in result.errors)

    def test_passwords_match(self):
        assert passwords_match("Senha1234", "Senha1234") is True
        assert passwords_match("Senha1234", "Outra1234") is False
        assert passwords_match("", "") is False


class TestTimeInconsistencies:
    def test_entry_after_lunch_start_is_flagged(self):
        warnings = detect_time_inconsistencies(time(18, 0), time(12, 0), None, None)
        assert any(w.field == "lunch_start" for w in warnings)

    def test_lunch_return_before_lunch_start_is_flagged(self):
        warnings = detect_time_inconsistencies(time(8, 0), time(12, 30), time(11, 50), None)
        assert any(w.field == "lunch_end" for w in warnings)

    def test_exit_before_lunch_return_is_flagged(self):
        warnings = detect_time_inconsistencies(time(8, 0), time(12, 0), time(13, 0), time(12, 30))
        assert any(w.field == "exit_time" for w in warnings)

    def test_consistent_full_day_has_no_warnings(self):
        warnings = detect_time_inconsistencies(time(8, 0), time(12, 0), time(13, 0), time(18, 0))
        assert warnings == []

    def test_partial_day_with_only_entry_has_no_warnings(self):
        warnings = detect_time_inconsistencies(time(8, 0), None, None, None)
        assert warnings == []
