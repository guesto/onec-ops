"""Настройка логирования CLI."""

from __future__ import annotations

import logging
from pathlib import Path

_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def setup_logging(level: str = "INFO", log_file: Path | None = None) -> None:
    """Настраивает вывод логов в stderr и, при необходимости, в файл."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    formatter = logging.Formatter(_FORMAT)

    if not any(getattr(handler, "_onec_ops_console", False) for handler in root_logger.handlers):
        console_handler = logging.StreamHandler()
        console_handler._onec_ops_console = True  # type: ignore[attr-defined]
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    if log_file is None:
        return

    log_path = Path(log_file).resolve()
    if any(
        getattr(handler, "_onec_ops_log_path", None) == log_path
        for handler in root_logger.handlers
    ):
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler._onec_ops_log_path = log_path  # type: ignore[attr-defined]
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
