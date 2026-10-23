"""Проверки команд хранилища через общий CLI и runner."""

from __future__ import annotations

import subprocess

import pytest

from scripts.actions import get_actions
from scripts.lib.exceptions import OneCOpsError
from scripts.onec_ops import build_parser, main

REPO_ACTIONS = [action for action in get_actions() if action.name.startswith("repo-")]
ADD_USER_ARGS = ["--user", "dev", "--rights", "LockObjects"]


def _required_args(action):
    return ADD_USER_ARGS if action.name == "repo-add-user" else []


@pytest.fixture(autouse=True)
def subprocess_mock(mocker):
    return mocker.patch("scripts.lib.runner._execute", return_value=subprocess.CompletedProcess([], 0, "", ""))


@pytest.mark.parametrize("action", REPO_ACTIONS, ids=lambda action: action.name)
def test_storage_argument_required(action, capsys):
    with pytest.raises(SystemExit) as error:
        build_parser().parse_args([action.name])
    assert error.value.code == 2
    assert "--storage" in capsys.readouterr().err


@pytest.mark.parametrize("action", REPO_ACTIONS, ids=lambda action: action.name)
@pytest.mark.parametrize("ib_state", ["missing_argument", "missing_file"])
def test_validate_requires_file_ib(action, ib_state, tmp_path):
    ns = build_parser().parse_args(
        [action.name, "--storage", str(tmp_path), *_required_args(action)]
    )
    if ib_state == "missing_file":
        ns.ib = tmp_path
    with pytest.raises(OneCOpsError, match="--ib|1Cv8.1CD"):
        action.validate(ns)


@pytest.mark.parametrize("action", REPO_ACTIONS, ids=lambda action: action.name)
@pytest.mark.parametrize("dry_run", [False, True])
def test_cli_uses_runner_with_absolute_paths(
    action, dry_run, tmp_path, monkeypatch, mocker, subprocess_mock, caplog,
):
    monkeypatch.chdir(tmp_path)
    ib = tmp_path / "ib"
    ib.mkdir()
    (ib / "1Cv8.1CD").touch()
    storage = tmp_path / "storage"
    if action.name != "repo-create":
        storage.mkdir()
        (storage / "repository.data").touch()
    platform = tmp_path / "1cv8"
    platform.touch()
    platform.chmod(0o755)
    mocker.patch("scripts.onec_ops.check_environment")
    mocker.patch("scripts.lib.runner.shutil.which", return_value="/usr/bin/xvfb-run")
    args = ["--platform", str(platform), "--ib", "ib", action.name, "--storage", "storage"]
    if action.name == "repo-create":
        args += ["--user", "admin", "--password", "secret"]
        expected = [
            "/ConfigurationRepositoryF", str(storage),
            "/ConfigurationRepositoryCreate",
        ]
    elif action.name == "repo-add-user":
        args += [
            *ADD_USER_ARGS, "--password", "user-secret",
            "--storage-user", "admin", "--storage-password", "secret",
        ]
        expected = ["/ConfigurationRepositoryF", str(storage)]
    else:
        args += ["--storage-user", "admin", "--storage-password", "secret", "--force"]
        flag = (
            "/ConfigurationRepositoryBindCfg" if action.name == "repo-bind"
            else "/ConfigurationRepositoryUpdateCfg"
        )
        expected = [flag, "/ConfigurationRepositoryF", str(storage)]
    expected += ["/ConfigurationRepositoryN", "admin", "/ConfigurationRepositoryP", "secret"]
    if action.name == "repo-bind":
        expected += ["-forceBindAlreadyBindedUser", "-forceReplaceCfg"]
    elif action.name == "repo-update":
        args += ["--version", "42"]
        expected += ["-v", "42", "-force"]
    elif action.name == "repo-add-user":
        expected += [
            "/ConfigurationRepositoryAddUser", "-User", "dev",
            "-Pwd", "user-secret", "-Rights", "LockObjects",
        ]
    expected = ["DESIGNER", "/F", str(ib), "/DisableStartupDialogs", *expected]
    if dry_run:
        args += ["--dry-run"]
    with caplog.at_level("INFO"):
        assert main(args) == 0
    assert "secret" not in caplog.text
    assert "***" in caplog.text
    if dry_run:
        subprocess_mock.assert_not_called()
        assert str(storage) in caplog.text
        assert expected[4] in caplog.text
    else:
        subprocess_mock.assert_called_once()
        command = subprocess_mock.call_args.args[0]
        assert command[-len(expected) - 2 : -2] == expected
        assert command[-2] == "/Out"
        assert subprocess_mock.call_args.kwargs["timeout"] == 600
    assert storage.is_dir()
