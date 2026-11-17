"""Действие выгрузки конфигурации в XML."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext

from .base import Action
from .extension_target import validate_extension_target
from .partial_list import collect_items, remove_temp_list, write_temp_list

logger = logging.getLogger(__name__)


class DumpConfigAction(Action):
    """Выгружает конфигурацию 1С в каталог XML-файлов."""

    name = "dump-config"
    help = "Выгрузить конфигурацию в XML"
    requires_ib = True
    path_args = ("to", "list_file")

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
        parser.add_argument(
            "--object",
            action="append",
            dest="objects",
            help="Объект для частичной выгрузки, например Catalog.Клиенты. Можно повторять",
        )
        parser.add_argument(
            "--list-file",
            type=Path,
            help="Файл со списком объектов для частичной выгрузки (UTF-8, по одному в строке)",
        )

    def validate(self, ns: argparse.Namespace) -> None:
        """Проверяет ИБ, выбор расширений и каталог выгрузки."""
        super().validate(ns)
        validate_extension_target(ns, required=False)
        ns.partial_items = collect_items(ns, items_attr="objects", items_option="--object")
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
        list_path = getattr(ns, "partial_list_path", None)
        if list_path is not None:
            args += ["-listFile", str(list_path)]
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
        items = getattr(ns, "partial_items", None)
        if items:
            write_temp_list(ns, items)

    def cleanup(self, ns: argparse.Namespace) -> None:
        """Удаляет временный список объектов."""
        remove_temp_list(ns)
