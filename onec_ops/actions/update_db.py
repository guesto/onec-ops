"""Обновление конфигурации базы данных."""

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


class UpdateDbAction(Action):
    """Применяет к БД конфигурацию, уже загруженную в ИБ."""

    name = "update-db"
    help = "Обновить конфигурацию базы данных"
    requires_ib = True

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Добавляет выбор расширения и режимы обновления."""
        add_extension_target(parser)
        parser.add_argument(
            "--dynamic",
            action=argparse.BooleanOptionalAction,
            default=None,
            help="Динамическое обновление (-Dynamic+ / -Dynamic-)",
        )
        parser.add_argument(
            "--warnings-as-errors", action="store_true", help="Считать предупреждения ошибками"
        )

    def validate(self, ns: argparse.Namespace) -> None:
        """Проверяет ИБ и необязательный выбор расширения."""
        super().validate(ns)
        validate_extension_target(ns, required=False)

    def build_1c_args(self, ns: argparse.Namespace, ctx: RunContext) -> list[str]:
        """Собирает команду UpdateDBCfg."""
        args = [
            "DESIGNER",
            "/F",
            str(ns.ib),
            "/DisableStartupDialogs",
            "/UpdateDBCfg",
            *extension_target_args(ns),
        ]
        if ns.dynamic is not None:
            args += ["-Dynamic+" if ns.dynamic else "-Dynamic-"]
        if ns.warnings_as_errors:
            args += ["-WarningsAsErrors"]
        return args

    def pre_run(self, ns: argparse.Namespace, ctx: RunContext) -> None:
        """Предупреждает о потере данных удалённых объектов."""
        logger.warning(
            "Объекты, удалённые из конфигурации, будут удалены из БД вместе с данными: %s", ns.ib
        )

    def post_run(
        self, ns: argparse.Namespace, ctx: RunContext, result: subprocess.CompletedProcess[str]
    ) -> None:
        """Сообщает, изменилась ли конфигурация БД."""
        if ctx.dry_run:
            return
        if getattr(result, "out_text", ""):
            logger.info("Конфигурация БД обновлена")
        else:
            logger.info("Изменений нет: конфигурация БД актуальна")
