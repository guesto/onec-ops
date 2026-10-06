"""Действие выгрузки конфигурации в XML."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext

from .base import Action

logger = logging.getLogger(__name__)


class DumpConfigAction(Action):
    """Выгружает конфигурацию 1С в каталог XML-файлов."""

    name = "dump-config"
    help = "Выгрузить конфигурацию в XML"
    requires_ib = True
    path_args = ("to",)

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Добавляет аргументы dump-config."""
        parser.add_argument("--to", type=Path, required=True, help="Каталог выгрузки XML")
        parser.add_argument(
            "--format",
            choices=("hierarchical", "plain"),
            default=None,
            help="Формат выгрузки. По умолчанию платформа выбирает сама "
            "(обычно hierarchical). Явно указывать не рекомендуется — "
            "не все версии платформы поддерживают этот параметр.",
        )
        parser.add_argument("--extension", help="Имя расширения конфигурации")
        parser.add_argument(
            "--all-extensions", action="store_true", help="Выгрузить все расширения"
        )

    def validate(self, ns: argparse.Namespace) -> None:
        """Проверяет ИБ, выбор расширений и каталог выгрузки."""
        super().validate(ns)
        if ns.extension and ns.all_extensions:
            raise OneCOpsError("--extension и --all-extensions взаимоисключающие.")
        if ns.to is None:
            raise OneCOpsError("Обязательно укажите --to.")
        path = Path(ns.to).resolve()
        while not path.exists():
            path = path.parent
        if not path.is_dir():
            raise OneCOpsError(f"Путь выгрузки должен быть каталогом: {path}")
        if not os.access(path, os.W_OK | os.X_OK):
            raise OneCOpsError(f"Каталог выгрузки недоступен для записи: {path}")

    def build_1c_args(self, ns: argparse.Namespace, ctx: RunContext) -> list[str]:
        """Собирает DumpConfigToFiles для конфигурации или расширений."""
        args = [
            "DESIGNER",
            "/F",
            str(ns.ib),
            "/DisableStartupDialogs",
            "/DumpConfigToFiles",
            str(Path(ns.to).resolve()),
        ]
        if ns.format:
            args += ["-Format", ns.format]
        if ns.extension:
            args += ["-Extension", ns.extension]
        if ns.all_extensions:
            args += ["-AllExtensions"]
        return args

    def pre_run(self, ns: argparse.Namespace, ctx: RunContext) -> None:
        """Создаёт каталог и предупреждает о возможной перезаписи."""
        path = Path(ns.to).resolve()
        try:
            path.mkdir(parents=True, exist_ok=True)
            if any(path.iterdir()):
                logger.warning("Каталог выгрузки непустой, файлы могут быть перезаписаны: %s", path)
        except OSError as error:
            raise OneCOpsError(
                f"Не удалось подготовить каталог выгрузки {path}: {error}"
            ) from error
