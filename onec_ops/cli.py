"""Командная строка onec-ops."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from onec_ops import skill_install
from onec_ops.actions import get_actions
from onec_ops.actions.base import Action
from onec_ops.lib.config import default_config_path, describe_config, load_config, resolve_platform
from onec_ops.lib.exceptions import OneCFailed, OneCOpsError, PlatformNotFound
from onec_ops.lib.logging_setup import setup_logging
from onec_ops.lib.platform_check import check_environment
from onec_ops.lib.runner import RunContext, run_1c

logger = logging.getLogger(__name__)
_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """Добавляет общие параметры CLI."""
    parser.add_argument("--ib", type=Path, default=argparse.SUPPRESS, help="Путь к файловой ИБ")
    parser.add_argument("--ib-user", default=argparse.SUPPRESS, help="Пользователь ИБ (/N)")
    parser.add_argument(
        "--ib-password", default=argparse.SUPPRESS, help="Пароль пользователя ИБ (/P)"
    )
    parser.add_argument(
        "--os-auth",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Аутентификация ОС (/WA+) вместо --ib-user / --ib-password (экспериментально)",
    )
    parser.add_argument("--platform", type=Path, default=argparse.SUPPRESS, help="Путь к 1cv8")
    parser.add_argument(
        "--log-level", choices=_LOG_LEVELS, default=argparse.SUPPRESS, help="Уровень логирования"
    )
    parser.add_argument("--log-file", type=Path, default=argparse.SUPPRESS, help="Файл журнала")
    parser.add_argument(
        "--config",
        type=Path,
        default=argparse.SUPPRESS,
        help=f"TOML-конфиг (по умолчанию {default_config_path()})",
    )
    parser.add_argument(
        "--dry-run", action="store_true", default=argparse.SUPPRESS, help="Не запускать 1С"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=argparse.SUPPRESS,
        help="Таймаут в секундах (по умолчанию 600, у run-epf 120)",
    )


def _resolve_ib_auth(ns: argparse.Namespace, action: Action) -> None:
    """Выбирает способ входа в ИБ.

    --os-auth — аутентификация ОС, без пользователя и пароля. Иначе пользователь
    из параметров CLI, затем из переменных окружения.
    """
    user = getattr(ns, "ib_user", None)
    password = getattr(ns, "ib_password", None)
    os_auth = getattr(ns, "os_auth", False)
    if not action.requires_ib:
        if user is not None or password is not None or os_auth:
            raise OneCOpsError(
                f"--ib-user / --ib-password / --os-auth неприменимы к {action.name}: "
                "у новой ИБ нет пользователей."
            )
        ns.ib_user = ns.ib_password = None
        ns.os_auth = False
        return
    legacy_user, legacy_password = action.legacy_ib_auth(ns)
    if os_auth:
        if any(value is not None for value in (user, password, legacy_user, legacy_password)):
            raise OneCOpsError(
                "--os-auth нельзя сочетать с --ib-user / --ib-password: выберите один способ входа."
            )
        if os.environ.get("ONEC_OPS_IB_USER") or os.environ.get("ONEC_OPS_IB_PASSWORD"):
            logger.info("--os-auth: ONEC_OPS_IB_USER / ONEC_OPS_IB_PASSWORD не используются.")
        ns.ib_user = ns.ib_password = None
        ns.os_auth = True
        return
    ns.os_auth = False
    if user is not None and legacy_user is not None and user != legacy_user:
        raise OneCOpsError("--ib-user и --user заданы с разными значениями.")
    if password is not None and legacy_password is not None and password != legacy_password:
        raise OneCOpsError("--ib-password и --password заданы с разными значениями.")
    user = user if user is not None else legacy_user
    password = password if password is not None else legacy_password
    if user is None:
        user = os.environ.get("ONEC_OPS_IB_USER") or None
    if password is None:
        password = os.environ.get("ONEC_OPS_IB_PASSWORD")
    if password and not user:
        raise OneCOpsError("--ib-password требует --ib-user.")
    ns.ib_user = user
    ns.ib_password = password


def _version() -> str:
    try:
        return version("onec-ops")
    except PackageNotFoundError:
        return "unknown"


def build_parser() -> argparse.ArgumentParser:
    """Строит парсер командной строки."""
    parser = argparse.ArgumentParser(prog="onec-ops", description="Пакетные операции 1С")
    parser.add_argument("--version", action="version", version=f"%(prog)s {_version()}")
    _add_common_arguments(parser)
    subparsers = parser.add_subparsers(dest="action", required=True)
    for action in get_actions():
        action_parser = subparsers.add_parser(
            action.name, help=action.help, description=action.description
        )
        _add_common_arguments(action_parser)
        action.add_arguments(action_parser)
    skill_install.add_parser(subparsers)
    return parser


def _configure_stdout() -> None:
    """Не падает на символах, которых нет в кодировке вывода (канал на Windows)."""
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(errors="backslashreplace")


def main(argv: list[str] | None = None) -> int:
    """Запускает CLI и возвращает код завершения."""
    _configure_stdout()
    parser = build_parser()
    ns = parser.parse_args(argv)
    ns.log_level = getattr(ns, "log_level", "INFO")
    ns.log_file = getattr(ns, "log_file", None)
    ns.config = getattr(ns, "config", None)
    ns.platform = getattr(ns, "platform", None)
    ns.dry_run = getattr(ns, "dry_run", False)
    ns.timeout = getattr(ns, "timeout", None)
    try:
        setup_logging(ns.log_level, ns.log_file)
        if ns.action == skill_install.NAME:
            return skill_install.run(ns)
        config = load_config(ns.config)
        if ns.dry_run:
            logger.info("%s", describe_config(ns.config))
        action = next(item for item in get_actions() if item.name == ns.action)
        _resolve_ib_auth(ns, action)
        if ns.timeout is None:
            ns.timeout = action.default_timeout
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
        try:
            action.pre_run(ns, ctx)
            if not action.requires_gui:
                try:
                    result = run_1c(action.command_args(ns, ctx), ctx)
                except OneCFailed as error:
                    action.on_failed(ns, ctx, error)
                    raise
                action.post_run(ns, ctx, result)
        finally:
            action.cleanup(ns)
        return 0
    except PlatformNotFound as error:
        logger.error("%s\n%s", error, describe_config(ns.config))
        return 1
    except OneCOpsError as error:
        logger.error("%s", error)
        return 1
    except KeyboardInterrupt:
        logger.warning("Работа прервана пользователем")
        return 130


if __name__ == "__main__":
    sys.exit(main())
