"""Проверка готовности окружения к запуску 1С."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys

from .exceptions import XvfbNotAvailable
from .runner import RunContext, _check_platform

logger = logging.getLogger(__name__)


def _warn_missing_libraries(ctx: RunContext) -> None:
    """Предупреждает об отсутствующих динамических библиотеках Linux."""
    try:
        result = subprocess.run(
            ["ldd", str(ctx.platform_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as error:
        logger.warning("Не удалось проверить зависимости GTK через ldd: %s", error)
        return

    missing = [line.strip() for line in result.stdout.splitlines() if "not found" in line]
    if missing:
        logger.warning("У платформы 1С отсутствуют библиотеки: %s", "; ".join(missing))


def check_environment(ctx: RunContext) -> None:
    """Проверяет платформу, дисплей и зависимости Linux."""
    _check_platform(ctx.platform_path)
    if sys.platform == "win32":
        return
    if not os.environ.get("DISPLAY") and not shutil.which("xvfb-run"):
        raise XvfbNotAvailable("Нет DISPLAY и не найден xvfb-run. Установите xvfb или задайте DISPLAY.")
    _warn_missing_libraries(ctx)
