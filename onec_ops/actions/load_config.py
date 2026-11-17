"""Действие загрузки конфигурации из XML."""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext

from .base import Action
from .extension_target import validate_extension_target
from .partial_list import collect_items, remove_temp_list, write_temp_list


class LoadConfigAction(Action):
    """Загружает конфигурацию 1С из каталога XML-файлов."""

    name = "load-config"
    help = "Загрузить конфигурацию из XML"
    requires_ib = True
    path_args = ("from_", "list_file")

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Добавляет аргументы load-config."""
        parser.add_argument(
            "--from",
            dest="from_",
            type=Path,
            required=True,
            help="Каталог с XML-выгрузкой",
        )
        parser.add_argument("--extension", help="Имя расширения конфигурации")
        parser.add_argument(
            "--all-extensions", action="store_true", help="Загрузить все расширения"
        )
        parser.add_argument(
            "--update-db-cfg",
            action="store_true",
            help="Обновить конфигурацию БД после загрузки",
        )
        parser.add_argument(
            "--file",
            action="append",
            dest="files",
            help="Файл для частичной загрузки, путь относительно --from. Можно повторять",
        )
        parser.add_argument(
            "--list-file",
            type=Path,
            help="Файл со списком файлов для частичной загрузки (UTF-8, по одному в строке)",
        )

    def validate(self, ns: argparse.Namespace) -> None:
        """Проверяет ИБ, выбор расширений и исходную XML-выгрузку."""
        super().validate(ns)
        validate_extension_target(ns, required=False)
        if ns.from_ is None:
            raise OneCOpsError("Обязательно укажите --from.")
        path = Path(ns.from_)
        if not path.exists():
            raise OneCOpsError(f"Каталог --from не существует: {path}")
        if not path.is_dir():
            raise OneCOpsError(f"--from должен быть каталогом: {path}")
        items = collect_items(ns, items_attr="files", items_option="--file")
        ns.partial_items = None if items is None else [self._relative_item(path, i) for i in items]
        if ns.partial_items is not None or ns.extension or ns.all_extensions:
            return
        if not (path / "Configuration.xml").is_file():
            raise OneCOpsError(f"В каталоге --from отсутствует файл Configuration.xml: {path}")

    @staticmethod
    def _relative_item(root: Path, item: str) -> str:
        """Возвращает путь файла относительно --from; файл должен лежать внутри каталога."""
        root = root.resolve()
        resolved = (root / item).resolve()
        if not resolved.is_relative_to(root):
            raise OneCOpsError(f"Файл из списка находится вне каталога --from: {item}")
        if not resolved.is_file():
            raise OneCOpsError(f"Файл из списка не найден в каталоге --from: {item}")
        return str(resolved.relative_to(root))

    def build_1c_args(self, ns: argparse.Namespace, ctx: RunContext) -> list[str]:
        """Собирает LoadConfigFromFiles и необязательное обновление БД."""
        args = [
            "DESIGNER",
            "/F",
            str(ns.ib),
            "/DisableStartupDialogs",
            "/LoadConfigFromFiles",
            str(Path(ns.from_).resolve()),
        ]
        list_path = getattr(ns, "partial_list_path", None)
        if list_path is not None:
            # -updateConfigDumpInfo переписал бы файл исходников, которого нет в списке.
            args += ["-listFile", str(list_path)]
        else:
            args += ["-updateConfigDumpInfo"]
        if ns.extension:
            args += ["-Extension", ns.extension]
        if ns.all_extensions:
            args += ["-AllExtensions"]
        if ns.update_db_cfg:
            args += ["/UpdateDBCfg"]
        return args

    def pre_run(self, ns: argparse.Namespace, ctx: RunContext) -> None:
        """Создаёт временный список файлов для частичной загрузки."""
        items = getattr(ns, "partial_items", None)
        if items:
            write_temp_list(ns, items)

    def cleanup(self, ns: argparse.Namespace) -> None:
        """Удаляет временный список файлов."""
        remove_temp_list(ns)
