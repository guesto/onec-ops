"""Разборка внешних обработок и отчётов в XML."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext

from .base import Action

logger = logging.getLogger(__name__)


class DumpEpfAction(Action):
    """Выгружает внешнюю обработку или отчёт в каталог XML-файлов."""

    name = "dump-epf"
    help = "Разобрать обработку или отчёт (.epf/.erf) в XML"
    requires_ib = True
    path_args = ("epf", "to")

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Добавляет входной файл и каталог XML-выгрузки."""
        parser.add_argument("--epf", type=Path, required=True, help="Входной файл .epf или .erf")
        parser.add_argument("--to", type=Path, required=True, help="Каталог XML-выгрузки")

    def validate(self, ns: argparse.Namespace) -> None:
        """Проверяет ИБ, входной файл и доступность каталога выгрузки."""
        super().validate(ns)
        if ns.epf is None:
            raise OneCOpsError("Обязательно укажите --epf.")
        epf = Path(ns.epf)
        if not epf.exists():
            raise OneCOpsError(f"Файл --epf не существует: {epf}")
        if not epf.is_file():
            raise OneCOpsError(f"--epf должен быть файлом: {epf}")
        if epf.stat().st_size == 0:
            raise OneCOpsError(f"Файл --epf пустой: {epf}")
        if epf.suffix.lower() not in (".epf", ".erf"):
            raise OneCOpsError(f"Файл --epf должен иметь расширение .epf или .erf: {epf}")
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
        """Собирает команду 1С: сначала каталог XML, затем входной файл."""
        return [
            "DESIGNER",
            "/F",
            str(ns.ib),
            "/DisableStartupDialogs",
            "/DumpExternalDataProcessorOrReportToFiles",
            str(Path(ns.to).resolve()),
            str(Path(ns.epf).resolve()),
        ]

    def pre_run(self, ns: argparse.Namespace, ctx: RunContext) -> None:
        """Создаёт каталог выгрузки и предупреждает о перезаписи."""
        path = Path(ns.to).resolve()
        try:
            path.mkdir(parents=True, exist_ok=True)
            if any(path.iterdir()):
                logger.warning("Каталог выгрузки непустой, файлы могут быть перезаписаны: %s", path)
        except OSError as error:
            raise OneCOpsError(
                f"Не удалось подготовить каталог выгрузки {path}: {error}"
            ) from error
