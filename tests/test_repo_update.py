"""Тесты обновления конфигурации из файлового хранилища."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from scripts.actions.repo_update import RepoUpdateAction
from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext


@pytest.fixture
def ns(tmp_path):
    ib = tmp_path / "ib"
    ib.mkdir()
    (ib / "1Cv8.1CD").touch()
    parser = argparse.ArgumentParser()
    RepoUpdateAction().add_arguments(parser)
    parsed = parser.parse_args(["--storage", str(tmp_path / "storage")])
    parsed.ib = ib
    return parsed


@pytest.fixture
def ctx(tmp_path):
    return RunContext(tmp_path / "1cv8")


def _base_args(ns):
    return [
        "DESIGNER", "/F", str(ns.ib), "/DisableStartupDialogs",
        "/ConfigurationRepositoryUpdateCfg", "/ConfigurationRepositoryF",
        str(Path(ns.storage).resolve()),
    ]


def test_validate_missing_storage(ns):
    ns.storage = None
    with pytest.raises(OneCOpsError, match="--storage"):
        RepoUpdateAction().validate(ns)


def test_validate_storage_not_exists(ns):
    with pytest.raises(OneCOpsError, match="не существует"):
        RepoUpdateAction().validate(ns)


def test_validate_storage_is_file(ns):
    ns.storage.touch()
    with pytest.raises(OneCOpsError, match="должен быть каталогом"):
        RepoUpdateAction().validate(ns)


def test_validate_ok(ns):
    ns.storage.mkdir()
    RepoUpdateAction().validate(ns)


def test_build_1c_args_base(ns, ctx, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ns.storage = Path("storage")
    assert RepoUpdateAction().build_1c_args(ns, ctx) == _base_args(ns)


def test_build_1c_args_with_version(ns, ctx):
    ns.version = 42
    assert RepoUpdateAction().build_1c_args(ns, ctx) == [*_base_args(ns), "-v", "42"]


def test_build_1c_args_with_force(ns, ctx):
    ns.force = True
    assert RepoUpdateAction().build_1c_args(ns, ctx) == [*_base_args(ns), "-force"]


def test_build_1c_args_with_user_password(ns, ctx):
    ns.storage_user = "admin"
    ns.storage_password = "secret"
    assert RepoUpdateAction().build_1c_args(ns, ctx) == [
        *_base_args(ns), "/ConfigurationRepositoryN", "admin",
        "/ConfigurationRepositoryP", "secret",
    ]
