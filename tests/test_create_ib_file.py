"""Тесты действия create-ib."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from scripts.actions.create_ib_file import CreateIbFileAction
from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext


def _namespace(
    path: Path | None,
    *,
    ib_type: str = "file",
    force: bool = False,
    yes: bool = False,
) -> argparse.Namespace:
    return argparse.Namespace(
        path=path,
        ib_type=ib_type,
        force=force,
        yes=yes,
        server=None,
        ref=None,
    )


def test_server_type_reports_v011_placeholder(tmp_path):
    with pytest.raises(OneCOpsError, match="v0.1.1"):
        CreateIbFileAction().validate(_namespace(tmp_path, ib_type="server"))


def test_existing_database_without_force_is_rejected(tmp_path):
    (tmp_path / "1Cv8.1CD").touch()

    with pytest.raises(OneCOpsError, match="--force"):
        CreateIbFileAction().validate(_namespace(tmp_path))


def test_missing_database_without_force_is_allowed(tmp_path):
    CreateIbFileAction().validate(_namespace(tmp_path))


def test_force_with_yes_removes_and_proceeds(tmp_path, mocker):
    (tmp_path / "1Cv8.1CD").touch()
    action = CreateIbFileAction()
    namespace = _namespace(tmp_path, force=True, yes=True)
    remove_mock = mocker.patch("scripts.actions.create_ib_file.shutil.rmtree")

    action.validate(namespace)
    action.pre_run(namespace, RunContext(tmp_path / "1cv8"))

    remove_mock.assert_called_once_with(tmp_path.resolve())


def test_force_without_yes_in_non_tty_raises(tmp_path, monkeypatch, mocker):
    (tmp_path / "1Cv8.1CD").touch()
    stdin = mocker.Mock()
    stdin.isatty.return_value = False
    monkeypatch.setattr("scripts.actions.create_ib_file.sys.stdin", stdin)

    with pytest.raises(OneCOpsError, match="--force --yes"):
        CreateIbFileAction().validate(_namespace(tmp_path, force=True))


def test_force_with_confirmation_yes_proceeds(tmp_path, monkeypatch, mocker):
    (tmp_path / "1Cv8.1CD").touch()
    stdin = mocker.Mock()
    stdin.isatty.return_value = True
    stdin.readline.return_value = "Y\n"
    monkeypatch.setattr("scripts.actions.create_ib_file.sys.stdin", stdin)

    CreateIbFileAction().validate(_namespace(tmp_path, force=True))


def test_force_with_confirmation_no_cancels(tmp_path, monkeypatch, mocker):
    (tmp_path / "1Cv8.1CD").touch()
    stdin = mocker.Mock()
    stdin.isatty.return_value = True
    stdin.readline.return_value = "n\n"
    monkeypatch.setattr("scripts.actions.create_ib_file.sys.stdin", stdin)

    with pytest.raises(OneCOpsError, match="Отменено"):
        CreateIbFileAction().validate(_namespace(tmp_path, force=True))


def test_build_args_uses_absolute_path(tmp_path):
    relative_path = tmp_path / "database"
    args = CreateIbFileAction().build_1c_args(
        _namespace(relative_path), RunContext(tmp_path / "1cv8")
    )

    assert args == ["CREATEINFOBASE", f"File={relative_path.resolve()}", "/DisableStartupMessages"]
