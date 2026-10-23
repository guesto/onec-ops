"""Выбор расширения: --extension NAME или --all-extensions."""

from __future__ import annotations

import argparse

from scripts.lib.exceptions import OneCOpsError


def add_extension_target(parser: argparse.ArgumentParser) -> None:
    """Добавляет взаимоисключающие --extension и --all-extensions."""
    parser.add_argument("--extension", help="Имя расширения конфигурации")
    parser.add_argument("--all-extensions", action="store_true", help="Все расширения")


def validate_extension_target(ns: argparse.Namespace, *, required: bool = True) -> None:
    """Проверяет выбор расширения: не больше одного варианта, при required — ровно один."""
    if ns.extension is not None and ns.all_extensions:
        raise OneCOpsError("--extension и --all-extensions взаимоисключающие.")
    if required and ns.extension is None and not ns.all_extensions:
        raise OneCOpsError("Укажите --extension NAME или --all-extensions.")
    if ns.extension is not None and not ns.extension.strip():
        raise OneCOpsError("Имя расширения --extension не может быть пустым.")


def extension_target_args(ns: argparse.Namespace) -> list[str]:
    """Возвращает -Extension <имя>, -AllExtensions или пустой список без выбора."""
    if ns.all_extensions:
        return ["-AllExtensions"]
    return ["-Extension", ns.extension] if ns.extension is not None else []


def extension_target_label(ns: argparse.Namespace) -> str:
    """Возвращает описание выбранных расширений для журнала."""
    return "все расширения" if ns.all_extensions else f"расширение {ns.extension}"
