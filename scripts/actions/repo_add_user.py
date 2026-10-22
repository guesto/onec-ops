"""Добавление пользователя в файловое хранилище конфигурации."""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext

from .base import Action

RIGHTS = ("ReadOnly", "LockObjects", "ManageConfigurationVersions", "Administration")


class RepoAddUserAction(Action):
    """Добавляет пользователя в файловое хранилище конфигурации 1С."""

    name = "repo-add-user"
    help = "Добавить пользователя в хранилище"
    requires_ib = True
    path_args = ("storage",)

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Добавляет параметры нового пользователя и администратора хранилища."""
        parser.add_argument("--storage", type=Path, required=True, help="Каталог хранилища")
        parser.add_argument("--user", required=True, help="Имя нового пользователя")
        parser.add_argument("--password", help="Пароль нового пользователя")
        parser.add_argument("--rights", required=True, choices=RIGHTS, help="Права пользователя")
        parser.add_argument("--storage-user", help="Администратор хранилища")
        parser.add_argument("--storage-password", help="Пароль администратора хранилища")
        parser.add_argument(
            "--restore-deleted",
            action="store_true",
            help="Восстановить удалённого пользователя",
        )

    def validate(self, ns: argparse.Namespace) -> None:
        """Проверяет ИБ, каталог хранилища и имя пользователя."""
        super().validate(ns)
        if ns.storage is None:
            raise OneCOpsError("Обязательно укажите --storage.")
        path = Path(ns.storage)
        if not path.exists():
            raise OneCOpsError(f"Каталог --storage не существует: {path}")
        if not path.is_dir():
            raise OneCOpsError(f"--storage должен быть каталогом: {path}")
        if not ns.user or not ns.user.strip():
            raise OneCOpsError("Имя пользователя --user не может быть пустым.")

    def build_1c_args(self, ns: argparse.Namespace, ctx: RunContext) -> list[str]:
        """Собирает команду ConfigurationRepositoryAddUser."""
        args = [
            "DESIGNER",
            "/F",
            str(ns.ib),
            "/DisableStartupDialogs",
            "/ConfigurationRepositoryF",
            str(Path(ns.storage).resolve()),
        ]
        if ns.storage_user:
            args += ["/ConfigurationRepositoryN", ns.storage_user]
        if ns.storage_password:
            args += ["/ConfigurationRepositoryP", ns.storage_password]
        args += ["/ConfigurationRepositoryAddUser", "-User", ns.user]
        if ns.password:
            args += ["-Pwd", ns.password]
        args += ["-Rights", ns.rights]
        if ns.restore_deleted:
            args += ["-RestoreDeletedUser"]
        return args
