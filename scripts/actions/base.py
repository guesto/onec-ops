"""Базовый интерфейс действий CLI."""

from __future__ import annotations

import argparse
import logging
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext

logger = logging.getLogger(__name__)


class Action(ABC):
    """Базовый класс действия onec-ops."""

    name: str
    help: str
    description: str = ""
    requires_ib: bool = False
    requires_gui: bool = False
    """Требуется ли реальный DISPLAY (не Xvfb)."""
    path_args: tuple[str, ...] = ()
    legacy_ib_auth_options: bool = False
    """Принимает ли действие устаревшие --user / --password для пользователя ИБ."""

    @abstractmethod
    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Добавляет аргументы действия."""

    @abstractmethod
    def build_1c_args(self, ns: argparse.Namespace, ctx: RunContext) -> list[str]:
        """Собирает аргументы для запуска 1С."""

    def legacy_ib_auth(self, ns: argparse.Namespace) -> tuple[str | None, str | None]:
        """Возвращает пользователя ИБ из устаревших --user / --password."""
        if not self.legacy_ib_auth_options:
            return None, None
        user = getattr(ns, "user", None)
        password = getattr(ns, "password", None)
        if user is not None or password is not None:
            logger.warning("--user / --password устарели, используйте --ib-user / --ib-password.")
        return user, password

    def ib_auth_args(self, ns: argparse.Namespace) -> list[str]:
        """Возвращает ключи /N и /P пользователя ИБ."""
        if not self.requires_ib:
            return []
        user = getattr(ns, "ib_user", None)
        password = getattr(ns, "ib_password", None)
        if password and not user:
            raise OneCOpsError("--ib-password требует --ib-user.")
        if not user:
            return []
        args = ["/N", user]
        if password:
            args += ["/P", password]
        return args

    def command_args(self, ns: argparse.Namespace, ctx: RunContext) -> list[str]:
        """Собирает аргументы 1С с пользователем ИБ сразу после /F <ib>."""
        args = self.build_1c_args(ns, ctx)
        auth = self.ib_auth_args(ns)
        if not auth:
            return args
        index = args.index("/F") + 2 if "/F" in args else len(args)
        return [*args[:index], *auth, *args[index:]]

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
