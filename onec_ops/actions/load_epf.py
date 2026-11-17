"""Сборка внешних обработок и отчётов из XML."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext

from .base import Action


class LoadEpfAction(Action):
    """Собирает внешнюю обработку или отчёт из корневого XML-файла."""

    name = "load-epf"
    help = "Собрать обработку или отчёт (.epf/.erf) из XML"
    requires_ib = True
    path_args = ("root", "epf")

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Добавляет корневой XML и выходной файл обработки или отчёта."""
        parser.add_argument("--root", type=Path, required=True, help="Корневой XML-файл")
        parser.add_argument("--epf", type=Path, required=True, help="Выходной файл .epf или .erf")

    def validate(self, ns: argparse.Namespace) -> None:
        """Проверяет ИБ, XML-файл и родительский каталог выходного файла."""
        super().validate(ns)
        if ns.root is None:
            raise OneCOpsError("Обязательно укажите --root.")
        root = Path(ns.root)
        if not root.exists():
            raise OneCOpsError(f"Файл --root не существует: {root}")
        if not root.is_file():
            raise OneCOpsError(f"--root должен быть файлом: {root}")
        if root.stat().st_size == 0:
            raise OneCOpsError(f"Файл --root пустой: {root}")
        if root.suffix.lower() != ".xml":
            raise OneCOpsError(f"Файл --root должен иметь расширение .xml: {root}")
        if ns.epf is None:
            raise OneCOpsError("Обязательно укажите --epf.")
        epf = Path(ns.epf).resolve()
        if epf.exists() and not epf.is_file():
            raise OneCOpsError(f"Выходной --epf должен указывать на файл: {epf}")
        path = epf.parent
        while not path.exists():
            path = path.parent
        if not path.is_dir():
            raise OneCOpsError(f"Родительский путь --epf должен быть каталогом: {path}")
        if not os.access(path, os.W_OK | os.X_OK):
            raise OneCOpsError(f"Родительский каталог --epf недоступен для записи: {path}")

    def build_1c_args(self, ns: argparse.Namespace, ctx: RunContext) -> list[str]:
        """Собирает команду 1С: сначала корневой XML, затем выходной файл."""
        return [
            "DESIGNER",
            "/F",
            str(ns.ib),
            "/DisableStartupDialogs",
            "/LoadExternalDataProcessorOrReportFromFiles",
            str(Path(ns.root).resolve()),
            str(Path(ns.epf).resolve()),
        ]

    def pre_run(self, ns: argparse.Namespace, ctx: RunContext) -> None:
        """Создаёт родительские каталоги для выходного файла."""
        path = Path(ns.epf).resolve().parent
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise OneCOpsError(f"Не удалось создать каталог сборки {path}: {error}") from error
