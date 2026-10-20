"""Тесты создания файлового хранилища конфигурации."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from scripts.actions.repo_create import RepoCreateAction
from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext


@pytest.fixture
def ns(tmp_path):
    ib = tmp_path / "ib"
    ib.mkdir()
    (ib / "1Cv8.1CD").touch()
    parser = argparse.ArgumentParser()
    RepoCreateAction().add_arguments(parser)
    parsed = parser.parse_args(["--storage", str(tmp_path / "nested" / "storage")])
    parsed.ib = ib
    return parsed


@pytest.fixture
def ctx(tmp_path):
    return RunContext(tmp_path / "1cv8")


def _base_args(ns):
    return [
        "DESIGNER", "/F", str(ns.ib), "/DisableStartupDialogs",
        "/ConfigurationRepositoryF", str(Path(ns.storage).resolve()),
        "/ConfigurationRepositoryCreate",
    ]


def test_validate_missing_storage(ns):
    ns.storage = None
    with pytest.raises(OneCOpsError, match="--storage"):
        RepoCreateAction().validate(ns)


def test_validate_storage_parent_not_writable(ns, mocker):
    access = mocker.patch("scripts.actions.repo_create.os.access", return_value=False)
    with pytest.raises(OneCOpsError, match="недоступен для записи"):
        RepoCreateAction().validate(ns)
    assert access.call_args.args[0] == ns.storage.parent.parent


def test_validate_storage_exists_nonempty_warns(ns, caplog):
    ns.storage.mkdir(parents=True)
    original = ns.storage / "existing"
    original.write_bytes(b"storage data")
    with caplog.at_level("WARNING"):
        RepoCreateAction().validate(ns)
    assert "непустой" in caplog.text
    assert str(ns.storage) in caplog.text
    assert original.read_bytes() == b"storage data"


def test_validate_ok(ns):
    RepoCreateAction().validate(ns)
    assert not ns.storage.exists()


def test_validate_storage_is_file(ns):
    ns.storage.parent.mkdir()
    ns.storage.touch()
    with pytest.raises(OneCOpsError, match="должен быть каталогом"):
        RepoCreateAction().validate(ns)


def test_validate_storage_parent_is_file(ns):
    ns.storage.parent.touch()
    with pytest.raises(OneCOpsError, match="Родительский путь"):
        RepoCreateAction().validate(ns)


def test_build_1c_args_base(ns, ctx):
    assert ns.user == "Администратор"
    assert RepoCreateAction().build_1c_args(ns, ctx) == [
        *_base_args(ns), "/ConfigurationRepositoryN", "Администратор",
    ]


def test_build_1c_args_with_user_password(ns, ctx):
    ns.user = "admin"
    ns.password = "secret"
    assert RepoCreateAction().build_1c_args(ns, ctx) == [
        *_base_args(ns), "/ConfigurationRepositoryN", "admin",
        "/ConfigurationRepositoryP", "secret",
    ]


def test_build_1c_args_without_user(ns, ctx, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ns.storage = Path("storage")
    ns.user = ""
    assert RepoCreateAction().build_1c_args(ns, ctx) == _base_args(ns)


def test_pre_run_creates_directory(ns, ctx):
    RepoCreateAction().pre_run(ns, ctx)
    assert ns.storage.is_dir()
    assert not list(ns.storage.iterdir())
    RepoCreateAction().pre_run(ns, ctx)


def test_pre_run_directory_creation_error(ns, ctx, mocker):
    mocker.patch.object(Path, "mkdir", side_effect=PermissionError("denied"))
    with pytest.raises(OneCOpsError, match="Не удалось создать каталог хранилища"):
        RepoCreateAction().pre_run(ns, ctx)
