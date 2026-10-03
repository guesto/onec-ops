"""Реестр действий onec-ops."""

from __future__ import annotations

from .base import Action
from .create_ib_file import CreateIbFileAction


def get_actions() -> list[Action]:
    """Возвращает доступные действия CLI."""
    return [CreateIbFileAction()]
