"""GUI-действие open-designer."""

from __future__ import annotations

import argparse
import logging
import os
import sys

from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import (
    RunContext,
    _detect_codex_sandbox,
    _verify_display,
    run_1c,
    run_1c_popen,
)

from .base import Action

logger = logging.getLogger(__name__)


class OpenDesignerAction(Action):
    """Открывает интерактивный Конфигуратор 1С."""

    name = "open-designer"
    help = "Открыть Конфигуратор"
    description = "Открывает интерактивный Конфигуратор 1С."
    requires_ib = True
    requires_gui = True

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Добавляет параметры open-designer."""
        parser.add_argument("--user", help="Имя пользователя ИБ")
        parser.add_argument("--password", help="Пароль пользователя ИБ")
        parser.add_argument("--no-wait", action="store_true", help="Не ждать закрытия окна")

    def validate(self, ns: argparse.Namespace) -> None:
        """Проверяет ИБ и доступность интерактивного дисплея."""
        super().validate(ns)
        if getattr(ns, "dry_run", False) or sys.platform == "win32":
            return
        display = os.environ.get("DISPLAY")
        if not display:
            raise OneCOpsError(
                "GUI-команды требуют реальный DISPLAY. "
                "Выполните команду в терминале графической сессии пользователя.",
            )
        if not _verify_display(display):
            raise OneCOpsError(f"X-сервер на DISPLAY={display} не отвечает.")
        if _detect_codex_sandbox():
            raise OneCOpsError(
                "GUI-команды недоступны в sandbox-режиме Codex. "
                "Выполните команду в терминале пользователя.",
            )

    def build_1c_args(self, ns: argparse.Namespace, ctx: RunContext) -> list[str]:
        """Собирает интерактивную команду 1С."""
        args = ["DESIGNER", "/F", str(ns.ib)]
        if ns.user:
            args += ["/N", ns.user]
        if ns.password:
            args += ["/P", ns.password]
        return args

    def pre_run(self, ns: argparse.Namespace, ctx: RunContext) -> None:
        """Запускает окно один раз с ожиданием или без него."""
        ctx.requires_gui = True
        logger.info("Запуск GUI: %s", self.help)
        args = self.build_1c_args(ns, ctx)
        if ns.no_wait:
            process = run_1c_popen(args, ctx)
            if process is not None:
                logger.info("GUI запущен, PID: %s", process.pid)
        else:
            run_1c(args, ctx)
