"""Серверное хранилище конфигурации: --storage tcp://, http://, https://."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from onec_ops.actions import get_actions
from onec_ops.cli import build_parser, main
from onec_ops.lib.exceptions import OneCOpsError
from onec_ops.lib.storage import (
    is_server_storage,
    storage_arg,
    storage_location,
    validate_server_storage,
)

REPO_ACTIONS = [action for action in get_actions() if action.name.startswith("repo-")]
ADD_USER_ARGS = ["--user", "dev", "--rights", "LockObjects"]
URLS = [
    "tcp://localhost:1542/main",
    "TCP://crs.local/main",
    "http://web.local/repo/repo.1ccr",
    "https://web.local/repo/repo.1ccr",
]


def _required_args(action):
    return ADD_USER_ARGS if action.name == "repo-add-user" else []


@pytest.mark.parametrize("url", URLS)
def test_is_server_storage_true(url):
    assert is_server_storage(url)
    assert storage_arg(url) == url
    assert storage_location(url) == url


@pytest.mark.parametrize(
    "value", ["storage", "/srv/crs", "C:\\crs", "ftp://host/x", "tcp:/host/x", Path("tcp://x/y")]
)
def test_is_server_storage_false(value):
    assert not is_server_storage(value)


def test_storage_arg_keeps_local_path():
    assert storage_arg("some/dir") == Path("some/dir")


@pytest.mark.parametrize(
    ("url", "match"),
    [
        ("tcp:///main", "сервер"),
        ("tcp://localhost:1542", "имя хранилища"),
        ("tcp://localhost:1542/", "имя хранилища"),
    ],
)
def test_validate_server_storage_rejects_bad_url(url, match):
    with pytest.raises(OneCOpsError, match=match):
        validate_server_storage(url)


@pytest.fixture
def ib(tmp_path):
    ib = tmp_path / "ib"
    ib.mkdir()
    (ib / "1Cv8.1CD").touch()
    return ib


@pytest.mark.parametrize("action", REPO_ACTIONS, ids=lambda action: action.name)
@pytest.mark.parametrize("url", URLS)
def test_validate_accepts_server_url(action, url, ib):
    ns = build_parser().parse_args([action.name, "--storage", url, *_required_args(action)])
    ns.ib = ib
    action.resolve_paths(ns)
    assert ns.storage == url
    action.validate(ns)


@pytest.mark.parametrize("action", REPO_ACTIONS, ids=lambda action: action.name)
def test_validate_rejects_url_without_name(action, ib):
    ns = build_parser().parse_args(
        [action.name, "--storage", "tcp://localhost:1542", *_required_args(action)]
    )
    ns.ib = ib
    with pytest.raises(OneCOpsError, match="имя хранилища"):
        action.validate(ns)


def test_add_user_still_checks_user_for_server(ib):
    action = next(a for a in REPO_ACTIONS if a.name == "repo-add-user")
    ns = build_parser().parse_args(
        ["repo-add-user", "--storage", URLS[0], "--user", " ", "--rights", "LockObjects"]
    )
    ns.ib = ib
    with pytest.raises(OneCOpsError, match="--user"):
        action.validate(ns)


@pytest.mark.parametrize("action", REPO_ACTIONS, ids=lambda action: action.name)
def test_cli_passes_url_unchanged(action, tmp_path, monkeypatch, mocker, ib):
    monkeypatch.chdir(tmp_path)
    execute = mocker.patch(
        "onec_ops.lib.runner._execute", return_value=subprocess.CompletedProcess([], 0, "", "")
    )
    platform = tmp_path / "1cv8"
    platform.touch()
    platform.chmod(0o755)
    mocker.patch("onec_ops.cli.check_environment")
    mocker.patch("onec_ops.lib.runner.shutil.which", return_value="/usr/bin/xvfb-run")
    url = "tcp://localhost:1542/main"
    args = ["--platform", str(platform), "--ib", "ib", action.name, "--storage", url]
    args += _required_args(action)
    assert main(args) == 0
    command = execute.call_args.args[0]
    index = command.index("/ConfigurationRepositoryF")
    assert command[index + 1] == url
    assert not (tmp_path / "tcp:").exists()
