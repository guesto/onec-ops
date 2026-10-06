"""Действие выгрузки конфигурации в .cf."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext

from .base import Action

logger = logging.getLogger(__name__)


class DumpCfAction(Action):
    """Выгружает конфигурацию 1С в файл .cf."""

    name = "dump-cf"
    help = "Выгрузить конфигурацию в .cf"
    requires_ib = True
    path_args = ("to",)

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Добавляет аргументы dump-cf."""
        parser.add_argument("--to", type=Path, required=True, help="Путь к выходному .cf")

    def validate(self, ns: argparse.Namespace) -> None:
        """Проверяет ИБ и предупреждает о перезаписи файла."""
        super().validate(ns)
        if ns.to is None:
            raise OneCOpsError("Обязательно укажите --to.")
        path = Path(ns.to)
        if path.exists():
            if not path.is_file():
                raise OneCOpsError(f"--to должен указывать на файл: {path}")
            logger.warning("Файл выгрузки существует и будет перезаписан: %s", path)

    def build_1c_args(self, ns: argparse.Namespace, ctx: RunContext) -> list[str]:
        """Собирает DumpCfg для основной конфигурации."""
        return [
            "DESIGNER",
            "/F",
            str(ns.ib),
            "/DisableStartupDialogs",
            "/DumpCfg",
            str(Path(ns.to).resolve()),
        ]

    def pre_run(self, ns: argparse.Namespace, ctx: RunContext) -> None:
        """Создаёт родительский каталог выходного файла."""
        path = Path(ns.to).resolve().parent
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise OneCOpsError(f"Не удалось создать каталог выгрузки {path}: {error}") from error
