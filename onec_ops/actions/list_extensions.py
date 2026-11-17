"""Список расширений конфигурации в ИБ."""

from __future__ import annotations

import argparse
import logging
import re
import subprocess

from scripts.lib.runner import RunContext

from .base import Action

logger = logging.getLogger(__name__)
_IDENTIFIER = re.compile(r"[^\W\d]\w*")


def parse_extension_names(out_text: str) -> list[str]:
    """Выбирает имена расширений из /Out, отбрасывая сообщения 1С."""
    return [line.strip() for line in out_text.splitlines() if _IDENTIFIER.fullmatch(line.strip())]


class ListExtensionsAction(Action):
    """Печатает в stdout имена расширений ИБ, по одному в строке."""

    name = "list-extensions"
    help = "Список расширений конфигурации"
    requires_ib = True

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """У list-extensions нет собственных параметров."""

    def build_1c_args(self, ns: argparse.Namespace, ctx: RunContext) -> list[str]:
        """Собирает команду DumpDBCfgList."""
        return [
            "DESIGNER",
            "/F",
            str(ns.ib),
            "/DisableStartupDialogs",
            "/DumpDBCfgList",
            "-AllExtensions",
        ]

    def post_run(
        self, ns: argparse.Namespace, ctx: RunContext, result: subprocess.CompletedProcess[str]
    ) -> None:
        """Печатает имена расширений из текста /Out."""
        if ctx.dry_run:
            return
        names = parse_extension_names(getattr(result, "out_text", ""))
        if not names:
            logger.info("Расширений нет")
        for name in names:
            print(name)
