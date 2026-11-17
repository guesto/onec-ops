"""Создание файлового хранилища конфигурации."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext

from .base import Action

logger = logging.getLogger(__name__)


class RepoCreateAction(Action):
    """Создаёт файловое хранилище конфигурации 1С."""

    name = "repo-create"
    help = "Создать хранилище конфигурации"
    requires_ib = True
    path_args = ("storage",)

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Добавляет путь и учётные данные администратора хранилища."""
        parser.add_argument("--storage", type=Path, required=True, help="Каталог хранилища")
        parser.add_argument("--user", default="Администратор", help="Администратор хранилища")
        parser.add_argument("--password", help="Пароль администратора хранилища")

    def validate(self, ns: argparse.Namespace) -> None:
        """Проверяет ИБ и доступность родительского каталога для записи."""
        super().validate(ns)
        if ns.storage is None:
            raise OneCOpsError("Обязательно укажите --storage.")
        path = Path(ns.storage).resolve()
        if path.exists() and not path.is_dir():
            raise OneCOpsError(f"--storage должен быть каталогом: {path}")
        parent = path.parent
        while not parent.exists():
            parent = parent.parent
        if not parent.is_dir():
            raise OneCOpsError(f"Родительский путь --storage должен быть каталогом: {parent}")
        if not os.access(parent, os.W_OK | os.X_OK):
            raise OneCOpsError(f"Родительский каталог --storage недоступен для записи: {parent}")
        try:
            if path.exists() and any(path.iterdir()):
                logger.warning("Каталог хранилища существует и непустой: %s", path)
        except OSError as error:
            raise OneCOpsError(f"Не удалось прочитать каталог хранилища {path}: {error}") from error

    def build_1c_args(self, ns: argparse.Namespace, ctx: RunContext) -> list[str]:
        """Собирает команду ConfigurationRepositoryCreate."""
        args = [
            "DESIGNER",
            "/F",
            str(ns.ib),
            "/DisableStartupDialogs",
            "/ConfigurationRepositoryF",
            str(Path(ns.storage).resolve()),
            "/ConfigurationRepositoryCreate",
        ]
        if ns.user:
            args += ["/ConfigurationRepositoryN", ns.user]
        if ns.password:
            args += ["/ConfigurationRepositoryP", ns.password]
        return args

    def pre_run(self, ns: argparse.Namespace, ctx: RunContext) -> None:
        """Создаёт недостающие каталоги хранилища."""
        path = Path(ns.storage).resolve()
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise OneCOpsError(f"Не удалось создать каталог хранилища {path}: {error}") from error
