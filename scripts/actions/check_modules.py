"""Проверка модулей и конфигурации: /CheckModules и /CheckConfig."""

from __future__ import annotations

import argparse
import logging
import subprocess

from scripts.lib.exceptions import OneCFailed, OneCOpsError
from scripts.lib.runner import RunContext

from .base import Action
from .extension_target import (
    add_extension_target,
    extension_target_args,
    validate_extension_target,
)

logger = logging.getLogger(__name__)

FINDINGS_RETURNCODE = 101
"""Код 1С «есть замечания»; сбой запуска даёт другой код."""

CHECK_MODES = {
    "thin-client": "-ThinClient",
    "web-client": "-WebClient",
    "server": "-Server",
    "external-connection": "-ExternalConnection",
    "thick-client": "-ThickClientOrdinaryApplication",
}
"""Без режимов /CheckModules пропускает ошибки и возвращает 0, поэтому режим есть всегда."""


class _CheckAction(Action):
    """Общая логика команд проверки."""

    requires_ib = True
    check_args: tuple[str, ...] = ()

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Добавляет режимы, расширенную проверку и выбор расширения."""
        parser.add_argument(
            "--mode",
            action="append",
            choices=tuple(CHECK_MODES),
            dest="modes",
            help="Режим проверки, можно повторять. По умолчанию все режимы",
        )
        parser.add_argument(
            "--extended",
            action="store_true",
            help="Расширенная проверка (-ExtendedModulesCheck); предупреждения дают код 1",
        )
        add_extension_target(parser)

    def validate(self, ns: argparse.Namespace) -> None:
        """Проверяет ИБ и необязательный выбор расширения."""
        super().validate(ns)
        validate_extension_target(ns, required=False)

    def build_1c_args(self, ns: argparse.Namespace, ctx: RunContext) -> list[str]:
        """Собирает команду проверки с режимами в постоянном порядке."""
        modes = ns.modes or tuple(CHECK_MODES)
        args = [
            "DESIGNER",
            "/F",
            str(ns.ib),
            "/DisableStartupDialogs",
            *self.check_args,
            *(switch for mode, switch in CHECK_MODES.items() if mode in modes),
        ]
        if ns.extended:
            args += ["-ExtendedModulesCheck"]
        return args + extension_target_args(ns)

    def on_failed(self, ns: argparse.Namespace, ctx: RunContext, error: OneCFailed) -> None:
        """Отделяет замечания проверки от сбоя запуска 1С."""
        if error.returncode != FINDINGS_RETURNCODE:
            return
        _, _, findings = str(error).partition("\n")
        raise OneCOpsError(f"Найдены замечания 1С:\n{findings}") from error

    def post_run(
        self, ns: argparse.Namespace, ctx: RunContext, result: subprocess.CompletedProcess[str]
    ) -> None:
        """Сообщает об успешной проверке."""
        if ctx.dry_run:
            return
        logger.info("Проверка пройдена: %s", getattr(result, "out_text", "") or "замечаний нет")


class CheckModulesAction(_CheckAction):
    """Проверяет синтаксис модулей."""

    name = "check-modules"
    help = "Проверить синтаксис модулей"
    check_args = ("/CheckModules",)


class CheckConfigAction(_CheckAction):
    """Проверяет конфигурацию: логическую целостность, ссылки и модули."""

    name = "check-config"
    help = "Проверить конфигурацию"
    check_args = ("/CheckConfig", "-ConfigLogIntegrity", "-IncorrectReferences")
