"""Обновление конфигурации из хранилища."""

from __future__ import annotations

import argparse
from pathlib import Path

from onec_ops.lib.exceptions import OneCOpsError
from onec_ops.lib.runner import RunContext
from onec_ops.lib.storage import (
    STORAGE_HELP,
    is_server_storage,
    storage_arg,
    storage_location,
    validate_server_storage,
)

from .base import Action


class RepoUpdateAction(Action):
    """Обновляет конфигурацию базы из хранилища 1С."""

    name = "repo-update"
    help = "Обновить конфигурацию из хранилища"
    requires_ib = True
    path_args = ("storage",)

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Добавляет параметры хранилища и обновления."""
        parser.add_argument("--storage", type=storage_arg, required=True, help=STORAGE_HELP)
        parser.add_argument("--storage-user", help="Пользователь хранилища")
        parser.add_argument("--storage-password", help="Пароль пользователя хранилища")
        parser.add_argument("--version", type=int, help="Номер версии (по умолчанию последняя)")
        parser.add_argument("--force", action="store_true", help="Получить новые объекты")

    def validate(self, ns: argparse.Namespace) -> None:
        """Проверяет ИБ и существование каталога хранилища."""
        super().validate(ns)
        if ns.storage is None:
            raise OneCOpsError("Обязательно укажите --storage.")
        if is_server_storage(ns.storage):
            validate_server_storage(ns.storage)
            return
        path = Path(ns.storage)
        if not path.exists():
            raise OneCOpsError(f"Каталог --storage не существует: {path}")
        if not path.is_dir():
            raise OneCOpsError(f"--storage должен быть каталогом: {path}")

    def build_1c_args(self, ns: argparse.Namespace, ctx: RunContext) -> list[str]:
        """Собирает команду ConfigurationRepositoryUpdateCfg."""
        args = [
            "DESIGNER",
            "/F",
            str(ns.ib),
            "/DisableStartupDialogs",
            "/ConfigurationRepositoryF",
            storage_location(ns.storage),
        ]
        if ns.storage_user:
            args += ["/ConfigurationRepositoryN", ns.storage_user]
        if ns.storage_password:
            args += ["/ConfigurationRepositoryP", ns.storage_password]
        # Ключи команды (-force…) 1С читает только сразу после неё: после /P
        # они молча игнорируются.
        args += ["/ConfigurationRepositoryUpdateCfg"]
        if ns.version:
            args += ["-v", str(ns.version)]
        if ns.force:
            args += ["-force"]
        return args
