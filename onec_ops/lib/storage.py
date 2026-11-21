"""Адрес хранилища конфигурации: локальный каталог или сервер хранилища."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

from onec_ops.lib.exceptions import OneCOpsError

SERVER_SCHEMES = ("tcp", "http", "https")
STORAGE_HELP = "Каталог хранилища или адрес сервера хранилища (tcp://, http://, https://)"


def is_server_storage(value: object) -> bool:
    """Возвращает True, если --storage задан адресом сервера хранилища."""
    if not isinstance(value, str):
        return False
    scheme, sep, _ = value.partition("://")
    return bool(sep) and scheme.lower() in SERVER_SCHEMES


def storage_arg(value: str) -> str | Path:
    """Тип argparse для --storage: адрес сервера остаётся строкой, остальное — Path.

    Path здесь нельзя: он схлопывает «tcp://» в «tcp:/».
    """
    if is_server_storage(value):
        return value
    return Path(value)


def validate_server_storage(value: str) -> None:
    """Проверяет форму адреса сервера: схема://сервер[:порт]/имя_хранилища."""
    parts = urlsplit(value)
    if not parts.netloc:
        raise OneCOpsError(f"В адресе --storage не указан сервер: {value}")
    if not parts.path.strip("/"):
        raise OneCOpsError(
            f"В адресе --storage не указано имя хранилища "
            f"(ожидается {parts.scheme}://сервер[:порт]/имя): {value}"
        )


def storage_location(value: str | Path) -> str:
    """Значение для /ConfigurationRepositoryF: адрес сервера как есть или абсолютный путь."""
    if is_server_storage(value):
        return str(value)
    return str(Path(value).resolve())
