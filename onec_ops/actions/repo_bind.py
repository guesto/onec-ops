"""Подключение файловой ИБ к хранилищу конфигурации."""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext

from .base import Action


class RepoBindAction(Action):
    """Подключает базу к файловому хранилищу конфигурации 1С."""

    name = "repo-bind"
    help = "Подключить базу к хранилищу"
    requires_ib = True
    path_args = ("storage",)

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Добавляет параметры подключения к хранилищу."""
        parser.add_argument("--storage", type=Path, required=True, help="Каталог хранилища")
        parser.add_argument("--storage-user", help="Пользователь хранилища")
        parser.add_argument("--storage-password", help="Пароль пользователя хранилища")
        parser.add_argument("--force", action="store_true", help="Перезаписать конфигурацию базы")

    def validate(self, ns: argparse.Namespace) -> None:
        """Проверяет ИБ и существующий непустой каталог хранилища."""
        super().validate(ns)
        if ns.storage is None:
            raise OneCOpsError("Обязательно укажите --storage.")
        path = Path(ns.storage)
        if not path.exists():
            raise OneCOpsError(f"Каталог --storage не существует: {path}")
        if not path.is_dir():
            raise OneCOpsError(f"--storage должен быть каталогом: {path}")
        try:
            if not any(path.iterdir()):
                raise OneCOpsError(f"Каталог --storage пустой: {path}")
        except OSError as error:
            raise OneCOpsError(f"Не удалось прочитать каталог хранилища {path}: {error}") from error

    def build_1c_args(self, ns: argparse.Namespace, ctx: RunContext) -> list[str]:
        """Собирает команду ConfigurationRepositoryBindCfg."""
        args = [
            "DESIGNER",
            "/F",
            str(ns.ib),
            "/DisableStartupDialogs",
            "/ConfigurationRepositoryBindCfg",
            "/ConfigurationRepositoryF",
            str(Path(ns.storage).resolve()),
        ]
        if ns.storage_user:
            args += ["/ConfigurationRepositoryN", ns.storage_user]
        if ns.storage_password:
            args += ["/ConfigurationRepositoryP", ns.storage_password]
        if ns.force:
            args += ["-forceBindAlreadyBindedUser", "-forceReplaceCfg"]
        return args
