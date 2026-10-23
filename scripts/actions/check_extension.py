"""Проверка возможности применить расширения конфигурации."""

from __future__ import annotations

import argparse
import logging
import subprocess

from scripts.lib.runner import RunContext

from .base import Action
from .extension_target import (
    add_extension_target,
    extension_target_args,
    validate_extension_target,
)

logger = logging.getLogger(__name__)


class CheckExtensionAction(Action):
    """Проверяет, можно ли применить расширение к конфигурации ИБ."""

    name = "check-extension"
    help = "Проверить, можно ли применить расширение"
    requires_ib = True

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Добавляет выбор расширения."""
        add_extension_target(parser)

    def validate(self, ns: argparse.Namespace) -> None:
        """Проверяет ИБ и выбор расширения."""
        super().validate(ns)
        validate_extension_target(ns)

    def build_1c_args(self, ns: argparse.Namespace, ctx: RunContext) -> list[str]:
        """Собирает команду CheckCanApplyConfigurationExtensions."""
        return [
            "DESIGNER",
            "/F",
            str(ns.ib),
            "/DisableStartupDialogs",
            "/CheckCanApplyConfigurationExtensions",
            *extension_target_args(ns),
        ]

    def post_run(
        self, ns: argparse.Namespace, ctx: RunContext, result: subprocess.CompletedProcess[str]
    ) -> None:
        """Сообщает об успешной проверке."""
        if ctx.dry_run:
            return
        if ns.all_extensions:
            logger.info("Все расширения можно применить")
        else:
            logger.info("Расширение можно применить: %s", ns.extension)
