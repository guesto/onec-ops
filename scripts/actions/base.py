"""Базовый интерфейс действий CLI."""

from __future__ import annotations

import argparse
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext


class Action(ABC):
    """Базовый класс действия onec-ops."""

    name: str
    help: str
    description: str = ""
    requires_ib: bool = False
    requires_gui: bool = False
    """Требуется ли реальный DISPLAY (не Xvfb)."""
    path_args: tuple[str, ...] = ()

    @abstractmethod
    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Добавляет аргументы действия."""

    @abstractmethod
    def build_1c_args(self, ns: argparse.Namespace, ctx: RunContext) -> list[str]:
        """Собирает аргументы для запуска 1С."""

    def resolve_paths(self, ns: argparse.Namespace) -> None:
        """Преобразует объявленные пути в абсолютные."""
        if self.requires_ib and getattr(ns, "ib", None):
            ns.ib = Path(ns.ib).resolve()
        for name in self.path_args:
            value = getattr(ns, name, None)
            if value:
                setattr(ns, name, Path(value).resolve())

    def validate(self, ns: argparse.Namespace) -> None:
        """Проверяет обязательную файловую ИБ для действий с requires_ib."""
        if not self.requires_ib:
            return
        ib = getattr(ns, "ib", None)
        if ib is None:
            raise OneCOpsError("Для этого действия обязательно укажите --ib.")
        if not (Path(ib) / "1Cv8.1CD").is_file():
            raise OneCOpsError(f"Файловая ИБ --ib не содержит файл 1Cv8.1CD: {ib}")

    def pre_run(self, ns: argparse.Namespace, ctx: RunContext) -> None:
        """Выполняет подготовку перед запуском."""

    def post_run(
        self, ns: argparse.Namespace, ctx: RunContext, result: subprocess.CompletedProcess[str]
    ) -> None:
        """Выполняет пост-обработку результата."""
