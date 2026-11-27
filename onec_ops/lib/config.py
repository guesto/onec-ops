"""Загрузка конфигурации onec-ops."""

from __future__ import annotations

import logging
import os
import re
import sys
import tomllib
from pathlib import Path

from platformdirs import user_config_dir

from .exceptions import OneCOpsError

logger = logging.getLogger(__name__)

_LINUX_PLATFORM_ROOT = Path("/opt/1cv8/x86_64")
_WINDOWS_PLATFORM_ROOT = Path(r"C:\Program Files\1cv8")
_VERSION_RE = re.compile(r"\d+(?:\.\d+){3}")


def default_config_path() -> Path:
    r"""Путь к конфигу по умолчанию для текущей ОС.

    Linux: ``~/.config/onec-ops/config.toml`` (или ``$XDG_CONFIG_HOME``).
    Windows: ``%LOCALAPPDATA%\onec-ops\onec-ops\config.toml`` — platformdirs
    повторяет имя приложения как имя автора.
    """
    return Path(user_config_dir("onec-ops")) / "config.toml"


def describe_config(path: Path | None) -> str:
    """Описывает, какой конфиг используется и найден ли он (для сообщений об ошибках)."""
    config_path = path or default_config_path()
    source = "--config" if path else "по умолчанию"
    state = "найден" if config_path.is_file() else "не найден"
    return f"Конфиг ({source}): {config_path} — {state}"


def load_config(path: Path | None) -> dict:
    """Загружает TOML-конфиг или возвращает пустой словарь."""
    config_path = path or default_config_path()
    logger.debug("Конфиг: %s", config_path)
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
    """Выбирает путь к платформе и делает пользовательский путь абсолютным."""
    if cli_path is not None:
        platform_path = Path(cli_path)
    elif environment_path := os.environ.get("ONEC_OPS_PLATFORM"):
        platform_path = Path(environment_path)
    elif config_path := config.get("platform"):
        platform_path = Path(config_path)
    else:
        return find_latest_platform()
    return platform_path.absolute()


def _platform_layout() -> tuple[Path, Path]:
    """Каталог с версиями платформы и путь к 1cv8 внутри каталога версии."""
    if sys.platform == "win32":
        return _WINDOWS_PLATFORM_ROOT, Path("bin") / "1cv8.exe"
    return _LINUX_PLATFORM_ROOT, Path("1cv8")


def _is_executable(path: Path) -> bool:
    return path.is_file() and (sys.platform == "win32" or os.access(path, os.X_OK))


def find_latest_platform() -> Path:
    """Находит самую новую установленную версию платформы 1С.

    Linux: ``/opt/1cv8/x86_64/<версия>/1cv8``.
    Windows: ``C:\\Program Files\\1cv8\\<версия>\\bin\\1cv8.exe``.
    Версии сравниваются как числа (8.5.10 новее 8.5.9). Каталоги без
    исполняемого файла платформы пропускаются. Если версий нет, возвращается
    путь-шаблон ``<каталог>/<версия>/...``: его отклонит проверка платформы.
    """
    root, executable = _platform_layout()
    candidates: list[tuple[tuple[int, ...], Path]] = []
    try:
        entries = list(root.iterdir())
    except OSError:
        entries = []
    for entry in entries:
        if not _VERSION_RE.fullmatch(entry.name):
            continue
        platform_path = entry / executable
        if _is_executable(platform_path):
            version = tuple(int(part) for part in entry.name.split("."))
            candidates.append((version, platform_path))
    if not candidates:
        # Ошибку «платформа не найдена» выдаёт проверка окружения при запуске 1С,
        # после проверки аргументов: здесь возвращаем путь-шаблон для сообщения.
        placeholder = root / "<версия>" / executable
        logger.debug("В %s нет установленных версий платформы 1С", root)
        return placeholder
    version, platform_path = max(candidates)
    logger.info(
        "Платформа 1С: %s (самая новая из установленных: %s)",
        ".".join(map(str, version)),
        platform_path,
    )
    return platform_path
