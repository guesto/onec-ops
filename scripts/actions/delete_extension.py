"""Удаление расширения конфигурации из ИБ."""

from __future__ import annotations

import argparse
import logging
import sys

from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext

from .base import Action
from .extension_target import (
    add_extension_target,
    extension_target_args,
    extension_target_label,
    validate_extension_target,
)

logger = logging.getLogger(__name__)


class DeleteExtensionAction(Action):
    """Удаляет расширение конфигурации вместе с данными его объектов."""

    name = "delete-extension"
    help = "Удалить расширение из ИБ"
    requires_ib = True

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Добавляет выбор расширения и подтверждение."""
        add_extension_target(parser)
        parser.add_argument("--yes", action="store_true", help="Удалить без подтверждения (для CI)")

    def validate(self, ns: argparse.Namespace) -> None:
        """Проверяет ИБ и выбор расширения."""
        super().validate(ns)
        validate_extension_target(ns)

    def build_1c_args(self, ns: argparse.Namespace, ctx: RunContext) -> list[str]:
        """Собирает команду DeleteCfg."""
        return [
            "DESIGNER",
            "/F",
            str(ns.ib),
            "/DisableStartupDialogs",
            "/DeleteCfg",
            *extension_target_args(ns),
        ]

    def pre_run(self, ns: argparse.Namespace, ctx: RunContext) -> None:
        """Предупреждает о потере данных и запрашивает подтверждение."""
        label = extension_target_label(ns)
        logger.warning("Удаление из ИБ %s: %s. Данные объектов расширения будут потеряны.", ns.ib, label)
        if ns.yes:
            logger.warning("--yes: удаляю без подтверждения")
            return
        if not sys.stdin.isatty():
            raise OneCOpsError(
                "Удаление расширения требует интерактивного подтверждения. "
                "В неинтерактивной среде используйте --yes."
            )
        print(
            f"\nВНИМАНИЕ! Удаление из ИБ {ns.ib}: {label}.\n"
            "Данные объектов расширения будут потеряны.\n\n"
            "Для подтверждения введите Y: ",
            file=sys.stderr,
            end="",
            flush=True,
        )
        answer = sys.stdin.readline().strip().lower()
        if answer not in ("y", "yes"):
            raise OneCOpsError("Отменено пользователем.")
