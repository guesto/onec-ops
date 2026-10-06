"""Действие загрузки конфигурации из XML."""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext

from .base import Action


class LoadConfigAction(Action):
    """Загружает конфигурацию 1С из каталога XML-файлов."""

    name = "load-config"
    help = "Загрузить конфигурацию из XML"
    requires_ib = True
    path_args = ("from_",)

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

    def validate(self, ns: argparse.Namespace) -> None:
        """Проверяет ИБ, выбор расширений и исходную XML-выгрузку."""
        super().validate(ns)
        if ns.extension and ns.all_extensions:
            raise OneCOpsError("--extension и --all-extensions взаимоисключающие.")
        if ns.from_ is None:
            raise OneCOpsError("Обязательно укажите --from.")
        path = Path(ns.from_)
        if not path.exists():
            raise OneCOpsError(f"Каталог --from не существует: {path}")
        if not path.is_dir():
            raise OneCOpsError(f"--from должен быть каталогом: {path}")
        if not ns.extension and not (path / "Configuration.xml").is_file():
            raise OneCOpsError(f"В каталоге --from отсутствует файл Configuration.xml: {path}")

    def build_1c_args(self, ns: argparse.Namespace, ctx: RunContext) -> list[str]:
        """Собирает LoadConfigFromFiles и необязательное обновление БД."""
        args = [
            "DESIGNER",
            "/F",
            str(ns.ib),
            "/DisableStartupDialogs",
            "/LoadConfigFromFiles",
            str(Path(ns.from_).resolve()),
            "-updateConfigDumpInfo",
        ]
        if ns.extension:
            args += ["-Extension", ns.extension]
        if ns.all_extensions:
            args += ["-AllExtensions"]
        if ns.update_db_cfg:
            args += ["/UpdateDBCfg"]
        return args
