"""Реестр действий onec-ops."""

from __future__ import annotations

from .base import Action
from .check_extension import CheckExtensionAction
from .create_ib_file import CreateIbFileAction
from .delete_extension import DeleteExtensionAction
from .dump_cf import DumpCfAction
from .dump_config import DumpConfigAction
from .dump_dt import DumpDtAction
from .dump_epf import DumpEpfAction
from .list_extensions import ListExtensionsAction
from .load_cf import LoadCfAction
from .load_config import LoadConfigAction
from .load_epf import LoadEpfAction
from .open_designer import OpenDesignerAction
from .open_enterprise import OpenEnterpriseAction
from .repo_add_user import RepoAddUserAction
from .repo_bind import RepoBindAction
from .repo_create import RepoCreateAction
from .repo_update import RepoUpdateAction
from .restore_dt import RestoreDtAction
from .update_db import UpdateDbAction


def get_actions() -> list[Action]:
    """Возвращает доступные действия CLI."""
    return [
        CreateIbFileAction(),
        DumpConfigAction(),
        LoadConfigAction(),
        DumpCfAction(),
        LoadCfAction(),
        OpenDesignerAction(),
        OpenEnterpriseAction(),
        DumpEpfAction(),
        LoadEpfAction(),
        DumpDtAction(),
        RestoreDtAction(),
        RepoCreateAction(),
        RepoBindAction(),
        RepoUpdateAction(),
        RepoAddUserAction(),
        ListExtensionsAction(),
        CheckExtensionAction(),
        DeleteExtensionAction(),
        UpdateDbAction(),
    ]
