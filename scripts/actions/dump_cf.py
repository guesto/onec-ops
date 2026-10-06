"""Действие выгрузки конфигурации и расширений."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext

from .base import Action

logger = logging.getLogger(__name__)


class DumpCfAction(Action):
    """Выгружает конфигурацию 1С в файл .cf или .cfe."""

    name = "dump-cf"
    help = "Выгрузить конфигурацию (.cf) или расширение (.cfe)"
    requires_ib = True
    path_args = ("to",)

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Добавляет аргументы dump-cf."""
        parser.add_argument("--to", type=Path, required=True, help="Путь к выходному .cf или .cfe")

        parser.add_argument(
            "--extension",
            help="Имя расширения. Обязателен для файлов .cfe, запрещён для .cf.",
        )

    def validate(self, ns: argparse.Namespace) -> None:
        """Проверяет ИБ и предупреждает о перезаписи файла."""
        super().validate(ns)
        if ns.to is None:
            raise OneCOpsError("Обязательно укажите --to.")
        path = Path(ns.to)
        suffix = path.suffix.lower()
        if suffix == ".cfe" and not ns.extension:
            raise OneCOpsError("Для файлов .cfe требуется --extension.")
        if suffix == ".cf" and ns.extension:
            raise OneCOpsError("--extension запрещён для .cf.")
        if suffix not in (".cf", ".cfe"):
            logger.warning("Неизвестное расширение файла %s: ожидается .cf или .cfe", path)
        if path.exists():
            if not path.is_file():
                raise OneCOpsError(f"--to должен указывать на файл: {path}")
            logger.warning("Файл выгрузки существует и будет перезаписан: %s", path)

    def build_1c_args(self, ns: argparse.Namespace, ctx: RunContext) -> list[str]:
        """Собирает DumpCfg для конфигурации или расширения."""
        args = [
            "DESIGNER",
            "/F",
            str(ns.ib),
            "/DisableStartupDialogs",
            "/DumpCfg",
            str(Path(ns.to).resolve()),
        ]
        if ns.extension:
            args += ["-Extension", ns.extension]
        return args

    def pre_run(self, ns: argparse.Namespace, ctx: RunContext) -> None:
        """Создаёт родительский каталог выходного файла."""
        path = Path(ns.to).resolve().parent
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise OneCOpsError(f"Не удалось создать каталог выгрузки {path}: {error}") from error
