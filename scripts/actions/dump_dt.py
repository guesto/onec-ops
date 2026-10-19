"""Выгрузка информационной базы в .dt."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext

from .base import Action

logger = logging.getLogger(__name__)


class DumpDtAction(Action):
    """Выгружает файловую информационную базу 1С в .dt."""

    name = "dump-dt"
    help = "Выгрузить базу в .dt"
    requires_ib = True
    path_args = ("to",)

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Добавляет путь к выходному файлу .dt."""
        parser.add_argument("--to", type=Path, required=True, help="Путь к выходному .dt")

    def validate(self, ns: argparse.Namespace) -> None:
        """Проверяет ИБ и доступность родительского каталога для записи."""
        super().validate(ns)
        if ns.to is None:
            raise OneCOpsError("Обязательно укажите --to.")
        path = Path(ns.to).resolve()
        if path.suffix.lower() != ".dt":
            logger.warning("Неизвестное расширение файла %s: ожидается .dt", path)
        if path.exists() and not path.is_file():
            raise OneCOpsError(f"--to должен указывать на файл: {path}")
        parent = path.parent
        while not parent.exists():
            parent = parent.parent
        if not parent.is_dir():
            raise OneCOpsError(f"Родительский путь --to должен быть каталогом: {parent}")
        if not os.access(parent, os.W_OK | os.X_OK):
            raise OneCOpsError(f"Родительский каталог --to недоступен для записи: {parent}")

    def build_1c_args(self, ns: argparse.Namespace, ctx: RunContext) -> list[str]:
        """Собирает команду DumpIB."""
        return [
            "DESIGNER",
            "/F",
            str(ns.ib),
            "/DisableStartupDialogs",
            "/DumpIB",
            str(Path(ns.to).resolve()),
        ]

    def pre_run(self, ns: argparse.Namespace, ctx: RunContext) -> None:
        """Создаёт родительский каталог и предупреждает о перезаписи."""
        path = Path(ns.to).resolve()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise OneCOpsError(
                f"Не удалось создать каталог выгрузки {path.parent}: {error}"
            ) from error
        if path.exists():
            logger.warning("Файл выгрузки существует и будет перезаписан: %s", path)
