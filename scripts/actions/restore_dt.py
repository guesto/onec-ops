"""Восстановление информационной базы из .dt."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext

from .base import Action

logger = logging.getLogger(__name__)


class RestoreDtAction(Action):
    """Восстанавливает существующую файловую ИБ из .dt."""

    name = "restore-dt"
    help = "Восстановить базу из .dt"
    requires_ib = True
    path_args = ("from_",)

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Добавляет файл бэкапа и параметры подтверждения восстановления."""
        parser.add_argument(
            "--from", dest="from_", type=Path, required=True, help="Путь к файлу .dt"
        )
        parser.add_argument("--force", action="store_true", help="Перезаписать существующую ИБ")
        parser.add_argument(
            "--yes", action="store_true", help="Подтвердить --force без интерактива (для CI)"
        )

    def validate(self, ns: argparse.Namespace) -> None:
        """Проверяет существующую ИБ и непустой файл .dt."""
        super().validate(ns)
        if ns.from_ is None:
            raise OneCOpsError("Обязательно укажите --from.")
        path = Path(ns.from_)
        if not path.exists():
            raise OneCOpsError(f"Файл --from не существует: {path}")
        if not path.is_file():
            raise OneCOpsError(f"--from должен быть файлом: {path}")
        if path.stat().st_size == 0:
            raise OneCOpsError(f"Файл --from пустой: {path}")
        if path.suffix.lower() != ".dt":
            raise OneCOpsError(f"Файл --from должен иметь расширение .dt: {path}")

    def build_1c_args(self, ns: argparse.Namespace, ctx: RunContext) -> list[str]:
        """Собирает команду RestoreIB."""
        return [
            "DESIGNER",
            "/F",
            str(ns.ib),
            "/DisableStartupDialogs",
            "/RestoreIB",
            str(Path(ns.from_).resolve()),
        ]

    def pre_run(self, ns: argparse.Namespace, ctx: RunContext) -> None:
        """Предупреждает о потере данных и запрашивает подтверждение."""
        logger.warning("Данные и конфигурация ИБ будут перезаписаны из .dt: %s", ns.ib)
        if ns.force and ns.yes:
            logger.warning("--force --yes: восстанавливаю ИБ без подтверждения: %s", ns.ib)
            return
        if not sys.stdin.isatty():
            raise OneCOpsError(
                "Восстановление требует интерактивного подтверждения. "
                "В неинтерактивной среде используйте --force --yes."
            )
        print(
            f"\nВНИМАНИЕ! Данные и конфигурация ИБ {ns.ib} будут перезаписаны.\n\n"
            "Для подтверждения введите Y: ",
            file=sys.stderr,
            end="",
            flush=True,
        )
        answer = sys.stdin.readline().strip().lower()
        if answer not in ("y", "yes"):
            raise OneCOpsError("Отменено пользователем.")
