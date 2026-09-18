"""Execucao assincrona de chamadas bloqueantes (rede/Supabase) fora da UI thread.

Toda chamada de repository/service feita a partir de uma tela deve passar
por `AsyncTaskRunner.run(...)` em vez de ser chamada diretamente, para nunca
congelar a interface durante operacoes de rede.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

from PySide6.QtCore import QObject, QThread, Signal

from repositories.exceptions import RepositoryError

logger = logging.getLogger(__name__)


class _WorkerSignals(QObject):
    succeeded = Signal(object)
    failed = Signal(str)
    finished = Signal()


class _Worker(QThread):
    def __init__(self, fn: Callable[..., Any], args: tuple, kwargs: dict):
        super().__init__()
        self.signals = _WorkerSignals()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self) -> None:
        try:
            result = self._fn(*self._args, **self._kwargs)
        except RepositoryError as exc:
            self.signals.failed.emit(exc.friendly_message)
        except Exception:
            logger.exception("Erro inesperado em tarefa assincrona")
            self.signals.failed.emit("Ocorreu um erro inesperado. Tente novamente.")
        else:
            self.signals.succeeded.emit(result)
        finally:
            self.signals.finished.emit()


class AsyncTaskRunner(QObject):
    """Dispara funcoes bloqueantes em threads separadas e mantem referencia
    aos workers ativos (evitando que o garbage collector do Python os
    destrua antes de terminarem, um erro comum com QThread).
    """

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._active_workers: list[_Worker] = []

    def run(
        self,
        fn: Callable[..., Any],
        *args: Any,
        on_success: Callable[[Any], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        on_finished: Callable[[], None] | None = None,
        **kwargs: Any,
    ) -> None:
        worker = _Worker(fn, args, kwargs)

        if on_success:
            worker.signals.succeeded.connect(on_success)
        if on_error:
            worker.signals.failed.connect(on_error)

        def _cleanup() -> None:
            if on_finished:
                on_finished()
            if worker in self._active_workers:
                self._active_workers.remove(worker)

        worker.signals.finished.connect(_cleanup)
        self._active_workers.append(worker)
        worker.start()

    def shutdown(self) -> None:
        """Aguarda todos os workers ativos terminarem (usado ao fechar a janela)."""
        for worker in list(self._active_workers):
            worker.wait(5000)
