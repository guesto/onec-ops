"""Пакетный запуск внешней обработки в режиме 1С:Предприятие."""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from onec_ops.lib.eventlog import read_errors
from onec_ops.lib.exceptions import OneCFailed, OneCOpsError
from onec_ops.lib.runner import RunContext

from .base import Action

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 120
_HANG_HINT = (
    "Клиент 1С, скорее всего, ждёт ответа в окне. Частые причины:\n"
    "- окно «Предупреждение безопасности» при открытии обработки: у пользователя ИБ "
    "включена защита от опасных действий (её отключает администратор базы в "
    "Конфигураторе: Администрирование → Пользователи → снять флажок «Защита от "
    "опасных действий»; в базе без пользователей защита включена всегда);\n"
    "- исключение в коде обработки: 1С показывает окно ошибки;\n"
    "- обработка не вызывает ЗавершитьРаботуСистемы(Ложь) и остаётся открытой."
)


class RunEpfAction(Action):
    """Запускает внешнюю обработку через /Execute и ждёт завершения клиента."""

    name = "run-epf"
    help = "Запустить обработку .epf в режиме Предприятия без окна"
    description = (
        "Запускает внешнюю обработку в 1С:Предприятии (/Execute) и ждёт, пока клиент "
        "завершится. Без DISPLAY на Linux — через xvfb-run. Сообщения 1С (Сообщить) "
        "выводятся в stdout. Обработка должна сама вызвать ЗавершитьРаботуСистемы(Ложь)."
    )
    requires_ib = True
    default_timeout = DEFAULT_TIMEOUT
    path_args = ("epf",)

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Добавляет обработку и параметр запуска."""
        parser.add_argument("--epf", type=Path, required=True, help="Файл обработки .epf")
        parser.add_argument(
            "--param",
            "--c",
            dest="param",
            help="Параметр запуска (/C), в обработке — ПараметрЗапуска",
        )

    def validate(self, ns: argparse.Namespace) -> None:
        """Проверяет ИБ и файл обработки."""
        super().validate(ns)
        epf = Path(ns.epf)
        if not epf.is_file():
            raise OneCOpsError(f"Файл --epf не найден: {epf}")
        if epf.suffix.lower() != ".epf":
            raise OneCOpsError(f"--epf должен быть файлом .epf: {epf}")

    def pre_run(self, ns: argparse.Namespace, ctx: RunContext) -> None:
        """Готовит файл /Out и запоминает время запуска для журнала регистрации."""
        ns.started_at = datetime.now().astimezone()
        ns.out_file = None
        if ctx.dry_run:
            return
        fd, name = tempfile.mkstemp(prefix="onec-ops-out-", suffix=".txt")
        os.close(fd)
        ns.out_file = Path(name)

    def build_1c_args(self, ns: argparse.Namespace, ctx: RunContext) -> list[str]:
        """Собирает команду ENTERPRISE с /Execute и /Out."""
        args = [
            "ENTERPRISE",
            "/F",
            str(ns.ib),
            "/DisableStartupDialogs",
            "/DisableStartupMessages",
            "/Execute",
            str(Path(ns.epf).resolve()),
        ]
        if ns.param is not None:
            args += ["/C", ns.param]
        out_file = getattr(ns, "out_file", None)
        if out_file is not None:
            args += ["/Out", str(out_file)]
        return args

    def on_failed(self, ns: argparse.Namespace, ctx: RunContext, error: OneCFailed) -> None:
        """Добавляет к ошибке подсказку о зависании и ошибки журнала регистрации."""
        parts = [str(error)]
        if error.returncode == -1 and "не завершилась" in str(error):
            parts.append(_HANG_HINT)
        started_at = getattr(ns, "started_at", None)
        if started_at is not None:
            log_errors = read_errors(Path(ns.ib), started_at)
            if log_errors:
                parts.append("Ошибки в журнале регистрации:\n" + "\n---\n".join(log_errors))
        raise OneCFailed(
            "\n".join(parts),
            returncode=error.returncode,
            command=error.command,
            stderr=error.stderr,
        ) from error

    def post_run(
        self, ns: argparse.Namespace, ctx: RunContext, result: subprocess.CompletedProcess[str]
    ) -> None:
        """Выводит сообщения обработки в stdout."""
        if ctx.dry_run:
            return
        out_text = getattr(result, "out_text", "")
        if out_text:
            print(out_text)
        logger.info("Обработка выполнена: %s", ns.epf)

    def cleanup(self, ns: argparse.Namespace) -> None:
        """Удаляет временный файл /Out."""
        out_file = getattr(ns, "out_file", None)
        if out_file is not None:
            Path(out_file).unlink(missing_ok=True)
