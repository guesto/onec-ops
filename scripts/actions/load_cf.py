"""Действие загрузки конфигурации из .cf."""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext

from .base import Action


class LoadCfAction(Action):
    """Загружает конфигурацию 1С из файла .cf."""

    name = "load-cf"
    help = "Загрузить конфигурацию из .cf"
    requires_ib = True
    path_args = ("from_",)

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Добавляет аргументы load-cf."""
        parser.add_argument(
            "--from",
            dest="from_",
            type=Path,
            required=True,
            help="Путь к файлу .cf",
        )
        parser.add_argument(
            "--update-db-cfg",
            action="store_true",
            help="Обновить конфигурацию БД после загрузки",
        )

    def validate(self, ns: argparse.Namespace) -> None:
        """Проверяет ИБ и непустой входной файл."""
        super().validate(ns)
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
        """Собирает LoadCfg и необязательное обновление конфигурации БД."""
        args = [
            "DESIGNER",
            "/F",
            str(ns.ib),
            "/DisableStartupDialogs",
            "/LoadCfg",
            str(Path(ns.from_).resolve()),
        ]
        if ns.update_db_cfg:
            args += ["/UpdateDBCfg"]
        return args
