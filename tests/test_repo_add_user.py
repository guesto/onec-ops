"""Тесты добавления пользователя в файловое хранилище."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from scripts.actions.repo_add_user import RepoAddUserAction
from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext


def _parser():
    parser = argparse.ArgumentParser()
    RepoAddUserAction().add_arguments(parser)
    return parser


@pytest.fixture
def ns(tmp_path):
    ib = tmp_path / "ib"
    ib.mkdir()
    (ib / "1Cv8.1CD").touch()
    parsed = _parser().parse_args([
        "--storage", str(tmp_path / "storage"), "--user", "Разработчик2",
        "--rights", "LockObjects",
    ])
    parsed.ib = ib
    return parsed


@pytest.fixture
def ctx(tmp_path):
    return RunContext(tmp_path / "1cv8")


def _base_args(ns):
    return [
        "DESIGNER", "/F", str(ns.ib), "/DisableStartupDialogs",
        "/ConfigurationRepositoryF", str(Path(ns.storage).resolve()),
    ]


def _add_user_args(ns):
    return ["/ConfigurationRepositoryAddUser", "-User", ns.user]


def test_validate_missing_storage(ns):
    ns.storage = None
    with pytest.raises(OneCOpsError, match="--storage"):
        RepoAddUserAction().validate(ns)


def test_validate_storage_not_exists(ns):
    with pytest.raises(OneCOpsError, match="не существует"):
        RepoAddUserAction().validate(ns)


def test_validate_storage_is_file(ns):
    ns.storage.touch()
    with pytest.raises(OneCOpsError, match="должен быть каталогом"):
        RepoAddUserAction().validate(ns)


@pytest.mark.parametrize("user", ["", "   "])
def test_validate_empty_user(ns, user):
    ns.storage.mkdir()
    ns.user = user
    with pytest.raises(OneCOpsError, match="--user"):
        RepoAddUserAction().validate(ns)


def test_invalid_rights_rejected_by_parser(tmp_path, capsys):
    with pytest.raises(SystemExit) as error:
        _parser().parse_args([
            "--storage", str(tmp_path), "--user", "dev", "--rights", "Everything",
        ])
    assert error.value.code == 2
    assert "--rights" in capsys.readouterr().err


@pytest.mark.parametrize(
    "rights", ["ReadOnly", "LockObjects", "ManageConfigurationVersions", "Administration"],
)
def test_parser_accepts_all_rights(tmp_path, rights):
    parsed = _parser().parse_args([
        "--storage", str(tmp_path), "--user", "dev", "--rights", rights,
    ])
    assert parsed.rights == rights


def test_validate_ok(ns):
    ns.storage.mkdir()
    RepoAddUserAction().validate(ns)


def test_build_1c_args_minimal(ns, ctx, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ns.storage = Path("storage")
    assert RepoAddUserAction().build_1c_args(ns, ctx) == [
        *_base_args(ns), *_add_user_args(ns), "-Rights", "LockObjects",
    ]


def test_build_1c_args_with_passwords(ns, ctx):
    ns.password = "user-secret"
    ns.storage_user = "admin"
    ns.storage_password = "admin-secret"
    assert RepoAddUserAction().build_1c_args(ns, ctx) == [
        *_base_args(ns),
        "/ConfigurationRepositoryN", "admin",
        "/ConfigurationRepositoryP", "admin-secret",
        *_add_user_args(ns), "-Pwd", "user-secret", "-Rights", "LockObjects",
    ]


def test_build_1c_args_with_restore_deleted(ns, ctx):
    ns.restore_deleted = True
    assert RepoAddUserAction().build_1c_args(ns, ctx) == [
        *_base_args(ns), *_add_user_args(ns), "-Rights", "LockObjects", "-RestoreDeletedUser",
    ]
