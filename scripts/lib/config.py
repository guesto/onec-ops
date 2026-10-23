"""Загрузка конфигурации onec-ops."""

from __future__ import annotations

import os
import sys
import tomllib
from pathlib import Path

from platformdirs import user_config_dir

from .exceptions import OneCOpsError

_LINUX_PLATFORM = Path("/opt/1cv8/x86_64/8.5.1.1343/1cv8")
_WINDOWS_PLATFORM = Path(r"C:\Program Files\1cv8\8.5.1.1343\bin\1cv8.exe")


def load_config(path: Path | None) -> dict:
    """Загружает TOML-конфиг или возвращает пустой словарь."""
    config_path = path or Path(user_config_dir("onec-ops")) / "config.toml"
    try:
        if not config_path.exists():
            return {}
        with config_path.open("rb") as config_file:
            config = tomllib.load(config_file)
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError) as error:
        raise OneCOpsError(
            f"Не удалось загрузить конфигурационный файл {config_path}: {error}"
        ) from error
    if "platform" in config and not isinstance(config["platform"], str):
        raise OneCOpsError(
            f"Параметр platform в конфигурационном файле {config_path} должен быть строкой."
        )
    return config


def resolve_platform(cli_path: Path | None, config: dict) -> Path:
    """Выбирает путь к платформе по заданному приоритету."""
    if cli_path is not None:
        return Path(cli_path)
    if environment_path := os.environ.get("ONEC_OPS_PLATFORM"):
        return Path(environment_path)
    if config_path := config.get("platform"):
        return Path(config_path)
    return _WINDOWS_PLATFORM if sys.platform == "win32" else _LINUX_PLATFORM
