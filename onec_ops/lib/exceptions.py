"""Исключения утилиты onec-ops."""

from __future__ import annotations


class OneCOpsError(Exception):
    """Базовое исключение утилиты."""


class PlatformNotFound(OneCOpsError):
    """Платформа 1С не найдена или недоступна для запуска."""


class XvfbNotAvailable(OneCOpsError):
    """Для запуска без дисплея не найден xvfb-run."""


class OneCFailed(OneCOpsError):
    """1С завершилась с ошибкой."""

    def __init__(self, message: str, *, returncode: int, command: list[str], stderr: str) -> None:
        super().__init__(message)
        self.returncode = returncode
        self.command = command
        self.stderr = stderr
