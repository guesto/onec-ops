"""Действие загрузки конфигурации и расширений."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext

from .base import Action

logger = logging.getLogger(__name__)


class LoadCfAction(Action):
    """Загружает конфигурацию 1С из файла .cf или .cfe."""

    name = "load-cf"
    help = "Загрузить конфигурацию (.cf) или расширение (.cfe)"
    requires_ib = True
    path_args = ("from_",)

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Добавляет аргументы load-cf."""
        parser.add_argument(
            "--from",
            dest="from_",
            type=Path,
            required=True,
            help="Путь к файлу .cf или .cfe",
        )
        parser.add_argument(
            "--update-db-cfg",
            action="store_true",
            help="Обновить конфигурацию БД после загрузки",
        )

        parser.add_argument(
            "--extension",
            help="Имя расширения. Обязателен для файлов .cfe, запрещён для .cf.",
        )

    def validate(self, ns: argparse.Namespace) -> None:
        """Проверяет ИБ и непустой входной файл."""
        super().validate(ns)
        if ns.from_ is None:
            raise OneCOpsError("Обязательно укажите --from.")
        path = Path(ns.from_)
        suffix = path.suffix.lower()
        if suffix == ".cfe" and not ns.extension:
            raise OneCOpsError("Для файлов .cfe требуется --extension.")
        if suffix == ".cf" and ns.extension:
            raise OneCOpsError("--extension запрещён для .cf.")
        if suffix not in (".cf", ".cfe"):
            logger.warning("Неизвестное расширение файла %s: ожидается .cf или .cfe", path)
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
        if ns.extension:
            args += ["-Extension", ns.extension]
        if ns.update_db_cfg:
            args += ["/UpdateDBCfg"]
        return args
