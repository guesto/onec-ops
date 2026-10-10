"""Командная строка onec-ops."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.actions import get_actions
from scripts.lib.config import load_config, resolve_platform
from scripts.lib.exceptions import OneCOpsError
from scripts.lib.logging_setup import setup_logging
from scripts.lib.platform_check import check_environment
from scripts.lib.runner import RunContext, run_1c

logger = logging.getLogger(__name__)
_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """Добавляет общие параметры CLI."""
    parser.add_argument("--ib", type=Path, default=argparse.SUPPRESS, help="Путь к файловой ИБ")
    parser.add_argument("--platform", type=Path, default=argparse.SUPPRESS, help="Путь к 1cv8")
    parser.add_argument(
        "--log-level", choices=_LOG_LEVELS, default=argparse.SUPPRESS, help="Уровень логирования"
    )
    parser.add_argument("--log-file", type=Path, default=argparse.SUPPRESS, help="Файл журнала")
    parser.add_argument("--config", type=Path, default=argparse.SUPPRESS, help="TOML-конфиг")
    parser.add_argument("--dry-run", action="store_true", default=argparse.SUPPRESS, help="Не запускать 1С")
    parser.add_argument("--timeout", type=int, default=argparse.SUPPRESS, help="Таймаут в секундах")


def build_parser() -> argparse.ArgumentParser:
    """Строит парсер командной строки."""
    parser = argparse.ArgumentParser(prog="onec-ops", description="Пакетные операции 1С")
    _add_common_arguments(parser)
    subparsers = parser.add_subparsers(dest="action", required=True)
    for action in get_actions():
        action_parser = subparsers.add_parser(action.name, help=action.help, description=action.description)
        _add_common_arguments(action_parser)
        action.add_arguments(action_parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Запускает CLI и возвращает код завершения."""
    parser = build_parser()
    ns = parser.parse_args(argv)
    ns.log_level = getattr(ns, "log_level", "INFO")
    ns.log_file = getattr(ns, "log_file", None)
    ns.config = getattr(ns, "config", None)
    ns.platform = getattr(ns, "platform", None)
    ns.dry_run = getattr(ns, "dry_run", False)
    ns.timeout = getattr(ns, "timeout", 600)
    setup_logging(ns.log_level, ns.log_file)

    try:
        config = load_config(ns.config)
        action = next(item for item in get_actions() if item.name == ns.action)
        ctx = RunContext(
            platform_path=resolve_platform(ns.platform, config),
            log_file=ns.log_file,
            log_level=ns.log_level,
            dry_run=ns.dry_run,
            timeout=ns.timeout,
            requires_gui=action.requires_gui,
        )
        if not action.requires_gui:
            check_environment(ctx)
        action.resolve_paths(ns)
        action.validate(ns)
        if action.requires_gui and not ctx.dry_run:
            check_environment(ctx)
        action.pre_run(ns, ctx)
        if not action.requires_gui:
            result = run_1c(action.build_1c_args(ns, ctx), ctx)
            action.post_run(ns, ctx, result)
        return 0
    except OneCOpsError as error:
        logger.error("%s", error)
        return 1
    except KeyboardInterrupt:
        logger.warning("Работа прервана пользователем")
        return 130


if __name__ == "__main__":
    sys.exit(main())
