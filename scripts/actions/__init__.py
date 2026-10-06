"""Реестр действий onec-ops."""

from __future__ import annotations

from .base import Action
from .create_ib_file import CreateIbFileAction
from .dump_cf import DumpCfAction
from .dump_cfu import DumpCfuAction
from .dump_config import DumpConfigAction
from .load_cf import LoadCfAction
from .load_cfu import LoadCfuAction
from .load_config import LoadConfigAction


def get_actions() -> list[Action]:
    """Возвращает доступные действия CLI."""
    return [
        CreateIbFileAction(),
        DumpConfigAction(),
        LoadConfigAction(),
        DumpCfAction(),
        LoadCfAction(),
        DumpCfuAction(),
        LoadCfuAction(),
    ]
