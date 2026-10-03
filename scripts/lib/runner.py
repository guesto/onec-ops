"""Запуск платформы 1С."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from .exceptions import OneCFailed, PlatformNotFound, XvfbNotAvailable

logger = logging.getLogger(__name__)
_PASSWORD_OPTIONS = {"/p", "/configurationrepositoryp"}


@dataclass
class RunContext:
    """Параметры запуска платформы 1С."""

    platform_path: Path
    log_file: Path | None = None
    log_level: str = "INFO"
    dry_run: bool = False
    timeout: int = 600


def _check_platform(platform_path: Path) -> None:
    """Проверяет, что исполняемый файл платформы доступен."""
    if not platform_path.exists() or (sys.platform != "win32" and not os.access(platform_path, os.X_OK)):
        raise PlatformNotFound(f"Платформа 1С не найдена или не исполняема: {platform_path}")


def build_command(args: list[str], ctx: RunContext) -> list[str]:
    """Собирает команду запуска 1С с учётом окружения."""
    _check_platform(ctx.platform_path)
    platform = str(ctx.platform_path)

    if sys.platform == "win32" or os.environ.get("DISPLAY"):
        return [platform, *args]

    if shutil.which("xvfb-run"):
        return ["xvfb-run", "-a", platform, *args]

    raise XvfbNotAvailable("Нет DISPLAY и не найден xvfb-run. Установите xvfb или задайте DISPLAY.")


def _mask_passwords(command: list[str]) -> list[str]:
    """Возвращает копию команды без паролей."""
    masked = list(command)
    for index, value in enumerate(masked[:-1]):
        if value.lower() in _PASSWORD_OPTIONS:
            masked[index + 1] = "***"
    return masked


def run_1c(args: list[str], ctx: RunContext) -> subprocess.CompletedProcess[str]:
    """Запускает 1С и преобразует ошибки процесса в OneCFailed."""
    command = build_command(args, ctx)
    logged_command = _mask_passwords(command)
    logger.info("Команда 1С: %s", logged_command)

    if ctx.dry_run:
        logger.info("Dry-run: запуск 1С пропущен")
        return subprocess.CompletedProcess(command, 0, "", "")

    started_at = time.monotonic()
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=ctx.timeout,
        )
    except subprocess.TimeoutExpired as error:
        duration = time.monotonic() - started_at
        logger.error("1С превысила таймаут за %.2f с: %s", duration, logged_command)
        raise OneCFailed(
            f"1С не завершилась за {ctx.timeout} секунд. Возможные причины: "
            "открыт диалог, отсутствует база, проблемы с лицензией.",
            returncode=-1,
            command=command,
            stderr=str(error),
        ) from error

    duration = time.monotonic() - started_at
    logger.info("stdout 1С: %s", result.stdout)
    logger.info("stderr 1С: %s", result.stderr)
    logger.info("1С завершилась с кодом %s за %.2f с", result.returncode, duration)

    if result.returncode != 0:
        raise OneCFailed(
            f"1С завершилась с ненулевым кодом: {result.returncode}",
            returncode=result.returncode,
            command=command,
            stderr=result.stderr,
        )

    return result
