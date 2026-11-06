"""Список объектов или файлов для частичной выгрузки и загрузки XML."""

from __future__ import annotations

import argparse
import logging
import os
import tempfile
from pathlib import Path

from scripts.lib.exceptions import OneCOpsError

logger = logging.getLogger(__name__)


def read_list_file(path: Path) -> list[str]:
    """Читает непустые строки файла-списка в UTF-8; BOM и CRLF допускаются."""
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except OSError as error:
        raise OneCOpsError(f"Не удалось прочитать --list-file {path}: {error}") from error
    except UnicodeDecodeError as error:
        raise OneCOpsError(f"Файл --list-file {path} должен быть в кодировке UTF-8.") from error
    return [line.strip() for line in text.splitlines() if line.strip()]


def collect_items(
    ns: argparse.Namespace, *, items_attr: str, items_option: str
) -> list[str] | None:
    """Возвращает элементы списка или None, если запрошена полная операция.

    Пустой список отклоняется: получив его, платформа молча обработает всю
    конфигурацию и вернёт код 0.
    """
    values = getattr(ns, items_attr, None)
    list_file = getattr(ns, "list_file", None)
    if values is None and list_file is None:
        return None
    if values is not None and list_file is not None:
        raise OneCOpsError(f"{items_option} и --list-file взаимоисключающие.")
    if getattr(ns, "all_extensions", False):
        raise OneCOpsError(
            f"{items_option} и --list-file нельзя сочетать с --all-extensions. "
            "Укажите одно расширение: --extension NAME."
        )
    if values is not None:
        if any(not value.strip() for value in values):
            raise OneCOpsError(f"Значение {items_option} не может быть пустым.")
        return [value.strip() for value in values]
    items = read_list_file(list_file)
    if not items:
        raise OneCOpsError(f"Файл --list-file пуст: {list_file}")
    return items


def write_temp_list(ns: argparse.Namespace, items: list[str]) -> None:
    """Пишет временный список для -listFile и запоминает его в ns.partial_list_path."""
    try:
        fd, name = tempfile.mkstemp(prefix="onec-ops-list-", suffix=".txt")
        ns.partial_list_path = Path(name)
        with os.fdopen(fd, "w", encoding="utf-8-sig", newline="\n") as stream:
            stream.write("\n".join(items) + "\n")
    except OSError as error:
        raise OneCOpsError(f"Не удалось создать временный список: {error}") from error
    logger.info("Частичная операция, элементов: %d: %s", len(items), ", ".join(items))


def remove_temp_list(ns: argparse.Namespace) -> None:
    """Удаляет временный список, если он был создан."""
    path = getattr(ns, "partial_list_path", None)
    if path is None:
        return
    try:
        Path(path).unlink(missing_ok=True)
    except OSError as error:
        logger.warning("Не удалось удалить временный список %s: %s", path, error)
    ns.partial_list_path = None
