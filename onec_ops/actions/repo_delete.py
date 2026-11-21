"""Удаление файлового хранилища конфигурации."""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from pathlib import Path

from onec_ops.lib.exceptions import OneCOpsError
from onec_ops.lib.runner import RunContext
from onec_ops.lib.storage import is_server_storage, storage_arg

from .base import Action

logger = logging.getLogger(__name__)

REPOSITORY_MARKER = "1cv8ddb.1CD"


class RepoDeleteAction(Action):
    """Удаляет каталог файлового хранилища конфигурации без запуска 1С.

    У 1С нет пакетной команды удаления хранилища, поэтому удаляется каталог.
    """

    name = "repo-delete"
    help = "Удалить файловое хранилище"
    runs_1c = False

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Добавляет каталог хранилища и подтверждение."""
        parser.add_argument(
            "--storage", type=storage_arg, required=True, help="Каталог файлового хранилища"
        )
        parser.add_argument("--yes", action="store_true", help="Удалить без подтверждения (для CI)")

    def validate(self, ns: argparse.Namespace) -> None:
        """Проверяет, что --storage — каталог файлового хранилища."""
        if is_server_storage(ns.storage):
            raise OneCOpsError(
                "repo-delete удаляет только файловое хранилище: у 1С и crserver нет "
                "команды удаления. Серверное хранилище — подкаталог с его именем в "
                "каталоге данных crserver (ключ -d); удалите его при остановленном сервере."
            )
        path = Path(ns.storage)
        if not path.exists():
            raise OneCOpsError(f"Каталог --storage не существует: {path}")
        if path.is_symlink() or not path.is_dir():
            raise OneCOpsError(f"--storage должен быть каталогом: {path}")
        if not (path / REPOSITORY_MARKER).is_file():
            raise OneCOpsError(
                f"Каталог не похож на хранилище конфигурации (нет {REPOSITORY_MARKER}): {path}"
            )
        ns.storage = path.resolve()

    def build_1c_args(self, ns: argparse.Namespace, ctx: RunContext) -> list[str]:
        """1С не запускается."""
        return []

    def execute(self, ns: argparse.Namespace) -> None:
        """Подтверждает и удаляет каталог хранилища."""
        path = Path(ns.storage)
        logger.warning(
            "Удаление хранилища %s. Вся история версий будет потеряна; "
            "подключённые базы останутся привязаны к несуществующему хранилищу "
            "(отключите их заранее: repo-unbind).",
            path,
        )
        if ns.dry_run:
            logger.info("Dry-run: каталог хранилища не удалён: %s", path)
            return
        self._confirm(ns, path)
        try:
            shutil.rmtree(path)
        except OSError as error:
            raise OneCOpsError(f"Не удалось удалить хранилище {path}: {error}") from error
        logger.info("Хранилище удалено: %s", path)

    @staticmethod
    def _confirm(ns: argparse.Namespace, path: Path) -> None:
        if ns.yes:
            logger.warning("--yes: удаляю без подтверждения")
            return
        if not sys.stdin.isatty():
            raise OneCOpsError(
                "Удаление хранилища требует интерактивного подтверждения. "
                "В неинтерактивной среде используйте --yes."
            )
        print(
            f"\nВНИМАНИЕ! Будет удалено хранилище конфигурации {path}\n"
            "вместе со всей историей версий.\n\n"
            "Для подтверждения введите Y: ",
            file=sys.stderr,
            end="",
            flush=True,
        )
        answer = sys.stdin.readline().strip().lower()
        if answer not in ("y", "yes"):
            raise OneCOpsError("Отменено пользователем.")
