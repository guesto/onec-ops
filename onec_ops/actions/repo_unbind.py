"""Отключение файловой ИБ от хранилища конфигурации."""

from __future__ import annotations

import argparse

from onec_ops.lib.runner import RunContext

from .base import Action


class RepoUnbindAction(Action):
    """Отключает базу от хранилища конфигурации 1С (файлового или серверного).

    Адрес хранилища не нужен: база помнит, к какому хранилищу подключена.
    """

    name = "repo-unbind"
    help = "Отключить базу от хранилища"
    requires_ib = True

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Добавляет учётные данные хранилища и --force."""
        parser.add_argument("--storage-user", help="Пользователь хранилища")
        parser.add_argument("--storage-password", help="Пароль пользователя хранилища")
        parser.add_argument(
            "--force",
            action="store_true",
            help="Отключить без аутентификации в хранилище, игнорируя захваченные объекты",
        )

    def build_1c_args(self, ns: argparse.Namespace, ctx: RunContext) -> list[str]:
        """Собирает команду ConfigurationRepositoryUnbindCfg."""
        args = ["DESIGNER", "/F", str(ns.ib), "/DisableStartupDialogs"]
        if ns.storage_user:
            args += ["/ConfigurationRepositoryN", ns.storage_user]
        if ns.storage_password:
            args += ["/ConfigurationRepositoryP", ns.storage_password]
        args += ["/ConfigurationRepositoryUnbindCfg"]
        if ns.force:
            args += ["-force"]
        return args
