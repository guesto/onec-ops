"""Общие фикстуры тестов."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _clear_ib_auth_environment(monkeypatch):
    """Переменные пользователя ИБ из окружения разработчика не влияют на тесты."""
    monkeypatch.delenv("ONEC_OPS_IB_USER", raising=False)
    monkeypatch.delenv("ONEC_OPS_IB_PASSWORD", raising=False)
