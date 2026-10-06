"""Действие загрузки расширения из .cfu."""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext

from .base import Action


class LoadCfuAction(Action):
    """Загружает расширение конфигурации из файла .cfu."""

    name = "load-cfu"
    help = "Загрузить расширение из .cfu"
    requires_ib = True
    path_args = ("from_",)

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Добавляет аргументы load-cfu."""
        parser.add_argument(
            "--from",
            dest="from_",
            type=Path,
            required=True,
            help="Путь к файлу .cfu",
        )
        parser.add_argument("--extension", required=True, help="Имя расширения конфигурации")
        parser.add_argument(
            "--update-db-cfg",
            action="store_true",
            help="Обновить конфигурацию БД после загрузки",
        )

    def validate(self, ns: argparse.Namespace) -> None:
        """Проверяет ИБ, имя расширения и непустой входной файл."""
        super().validate(ns)
        if not ns.extension or not ns.extension.strip():
            raise OneCOpsError("Обязательно укажите --extension.")
        if ns.from_ is None:
            raise OneCOpsError("Обязательно укажите --from.")
        path = Path(ns.from_)
        if not path.exists():
            raise OneCOpsError(f"Файл --from не существует: {path}")
        if not path.is_file():
            raise OneCOpsError(f"--from должен быть файлом: {path}")
        if path.stat().st_size == 0:
            raise OneCOpsError(f"Файл --from пустой: {path}")

    def build_1c_args(self, ns: argparse.Namespace, ctx: RunContext) -> list[str]:
        """Собирает LoadCfg с выбором расширения и обновлением БД."""
        args = [
            "DESIGNER",
            "/F",
            str(ns.ib),
            "/DisableStartupDialogs",
            "/LoadCfg",
            str(Path(ns.from_).resolve()),
            "-Extension",
            ns.extension,
        ]
        if ns.update_db_cfg:
            args += ["/UpdateDBCfg"]
        return args
