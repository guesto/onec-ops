"""Тесты подключения базы к файловому хранилищу."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from scripts.actions.repo_bind import RepoBindAction
from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext


@pytest.fixture
def ns(tmp_path):
    ib = tmp_path / "ib"
    ib.mkdir()
    (ib / "1Cv8.1CD").touch()
    parser = argparse.ArgumentParser()
    RepoBindAction().add_arguments(parser)
    parsed = parser.parse_args(["--storage", str(tmp_path / "storage")])
    parsed.ib = ib
    return parsed


@pytest.fixture
def ctx(tmp_path):
    return RunContext(tmp_path / "1cv8")


def _base_args(ns):
    return [
        "DESIGNER", "/F", str(ns.ib), "/DisableStartupDialogs",
        "/ConfigurationRepositoryBindCfg", "/ConfigurationRepositoryF",
        str(Path(ns.storage).resolve()),
    ]


def test_validate_missing_storage(ns):
    ns.storage = None
    with pytest.raises(OneCOpsError, match="--storage"):
        RepoBindAction().validate(ns)


def test_validate_storage_not_exists(ns):
    with pytest.raises(OneCOpsError, match="не существует"):
        RepoBindAction().validate(ns)


def test_validate_storage_empty(ns):
    ns.storage.mkdir()
    with pytest.raises(OneCOpsError, match="пустой"):
        RepoBindAction().validate(ns)


def test_validate_storage_is_file(ns):
    ns.storage.touch()
    with pytest.raises(OneCOpsError, match="должен быть каталогом"):
        RepoBindAction().validate(ns)


def test_validate_ok(ns):
    ns.storage.mkdir()
    (ns.storage / "repository.data").touch()
    RepoBindAction().validate(ns)


def test_validate_storage_not_readable(ns, mocker):
    ns.storage.mkdir()
    mocker.patch.object(Path, "iterdir", side_effect=PermissionError("denied"))
    with pytest.raises(OneCOpsError, match="Не удалось прочитать каталог"):
        RepoBindAction().validate(ns)


def test_build_1c_args_base(ns, ctx, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ns.storage = Path("storage")
    assert RepoBindAction().build_1c_args(ns, ctx) == _base_args(ns)


def test_build_1c_args_with_force(ns, ctx):
    ns.force = True
    assert RepoBindAction().build_1c_args(ns, ctx) == [
        *_base_args(ns),
        "-forceBindAlreadyBindedUser",
        "-forceReplaceCfg",
    ]


def test_build_1c_args_with_user_password(ns, ctx):
    ns.storage_user = "admin"
    ns.storage_password = "secret"
    assert RepoBindAction().build_1c_args(ns, ctx) == [
        *_base_args(ns), "/ConfigurationRepositoryN", "admin",
        "/ConfigurationRepositoryP", "secret",
    ]
