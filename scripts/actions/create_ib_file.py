"""Действие создания файловой информационной базы."""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from pathlib import Path

from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext

from .base import Action

logger = logging.getLogger(__name__)


class CreateIbFileAction(Action):
    """Создаёт файловую информационную базу 1С."""

    name = "create-ib"
    help = "Создать информационную базу"
    requires_ib = False
    path_args = ("path",)

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Добавляет аргументы create-ib."""
        parser.add_argument("--type", choices=("file", "server"), required=True, dest="ib_type")
        parser.add_argument("--path", type=Path, help="Путь к файловой ИБ")
        parser.add_argument("--force", action="store_true", help="Перезаписать существующую ИБ")
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Подтвердить удаление без интерактива (для CI)",
        )
        parser.add_argument("--server", help="Сервер 1С")
        parser.add_argument("--ref", help="Имя ИБ на сервере")

    def validate(self, ns: argparse.Namespace) -> None:
        """Проверяет параметры создания ИБ."""
        if ns.ib_type == "server":
            raise OneCOpsError(
                "Клиент-серверная ИБ будет реализована в v0.1.1. Сейчас используйте --type file."
            )
        if ns.path is None:
            raise OneCOpsError("Для --type file обязательно укажите --path.")
        database_file = Path(ns.path) / "1Cv8.1CD"
        if not database_file.exists():
            return
        if not ns.force:
            raise OneCOpsError(
                f"ИБ уже существует: {ns.path}. Если вы уверены, что хотите "
                "её удалить и создать заново, запустите с флагом --force."
            )
        if ns.yes:
            logger.warning("--force --yes: удаляю существующую ИБ: %s", ns.path)
            return
        if not sys.stdin.isatty():
            raise OneCOpsError(
                "--force требует интерактивного подтверждения. "
                "В неинтерактивной среде используйте --force --yes."
            )
        print(
            f"\nВНИМАНИЕ! Каталог {ns.path} будет полностью удалён,\n"
            "включая все данные и файл 1Cv8.1CD.\n\n"
            "Для подтверждения введите Y: ",
            file=sys.stderr,
            end="",
            flush=True,
        )
        answer = sys.stdin.readline().strip()
        if not answer or answer[0].lower() != "y":
            raise OneCOpsError("Отменено пользователем.")

    def build_1c_args(self, ns: argparse.Namespace, ctx: RunContext) -> list[str]:
        """Собирает CREATEINFOBASE для файловой ИБ."""
        return ["CREATEINFOBASE", f"File={Path(ns.path).resolve()}", "/DisableStartupMessages"]

    def pre_run(self, ns: argparse.Namespace, ctx: RunContext) -> None:
        """Удаляет существующую ИБ и создаёт её каталог."""
        if ns.ib_type != "file":
            return
        path = Path(ns.path).resolve()
        if ns.force and (path / "1Cv8.1CD").exists():
            logger.warning("Удаляю существующую ИБ: %s", path)
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)
