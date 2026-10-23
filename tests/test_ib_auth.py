"""Тесты пользователя ИБ (/N, /P) для команд с --ib."""

from __future__ import annotations

import argparse
import subprocess

import pytest

from scripts.actions import get_actions
from scripts.actions.dump_cf import DumpCfAction
from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext
from scripts.onec_ops import _resolve_ib_auth, build_parser, main

IB_ACTIONS = {action.name: action for action in get_actions() if action.requires_ib}
ACTION_ARGS = {
    "dump-config": ["--to", "xml"],
    "load-config": ["--from", "xml"],
    "dump-cf": ["--to", "base.cf"],
    "load-cf": ["--from", "base.cf"],
    "dump-epf": ["--epf", "a.epf", "--to", "xml"],
    "load-epf": ["--root", "a.xml", "--epf", "a.epf"],
    "dump-dt": ["--to", "base.dt"],
    "restore-dt": ["--from", "base.dt"],
    "repo-create": ["--storage", "storage"],
    "repo-bind": ["--storage", "storage"],
    "repo-update": ["--storage", "storage"],
    "repo-add-user": ["--storage", "storage", "--user", "dev", "--rights", "ReadOnly"],
    "list-extensions": [],
    "check-extension": ["--extension", "ext"],
    "delete-extension": ["--all-extensions", "--yes"],
    "update-db": [],
    "open-designer": [],
    "open-enterprise": [],
}


@pytest.fixture
def ctx(tmp_path):
    return RunContext(tmp_path / "1cv8")


def _ns(**values):
    return argparse.Namespace(ib="/ib", **values)


def test_all_ib_actions_covered():
    assert set(IB_ACTIONS) == set(ACTION_ARGS)


def test_ib_auth_args_without_user():
    assert DumpCfAction().ib_auth_args(_ns()) == []


def test_ib_auth_args_user_without_password():
    assert DumpCfAction().ib_auth_args(_ns(ib_user="admin", ib_password=None)) == ["/N", "admin"]


def test_ib_auth_args_empty_password():
    assert DumpCfAction().ib_auth_args(_ns(ib_user="admin", ib_password="")) == ["/N", "admin"]


def test_ib_auth_args_user_and_password():
    assert DumpCfAction().ib_auth_args(_ns(ib_user="admin", ib_password="secret")) == [
        "/N", "admin", "/P", "secret",
    ]


def test_ib_auth_args_password_without_user():
    with pytest.raises(OneCOpsError, match="--ib-password требует --ib-user"):
        DumpCfAction().ib_auth_args(_ns(ib_user=None, ib_password="secret"))


def test_ib_auth_args_ignored_without_requires_ib():
    action = next(item for item in get_actions() if item.name == "create-ib")
    assert action.ib_auth_args(_ns(ib_user="admin", ib_password="secret")) == []


@pytest.mark.parametrize("name", sorted(ACTION_ARGS))
@pytest.mark.parametrize("position", ["before", "after"])
def test_command_args_insert_auth_after_ib(name, position, ctx):
    common = ["--ib", "/ib", "--ib-user", "admin", "--ib-password", "secret"]
    if position == "before":
        argv = [*common, name, *ACTION_ARGS[name]]
    else:
        argv = [name, *common, *ACTION_ARGS[name]]
    ns = build_parser().parse_args(argv)
    action = IB_ACTIONS[name]
    _resolve_ib_auth(ns, action)
    action.resolve_paths(ns)
    args = action.command_args(ns, ctx)
    index = args.index("/F")
    assert args[index + 2:index + 6] == ["/N", "admin", "/P", "secret"]
    assert args.count("/N") == 1


def test_command_args_without_auth_unchanged(ctx, tmp_path):
    ns = build_parser().parse_args(["--ib", str(tmp_path), "dump-cf", "--to", "base.cf"])
    action = IB_ACTIONS["dump-cf"]
    _resolve_ib_auth(ns, action)
    assert action.command_args(ns, ctx) == action.build_1c_args(ns, ctx)


def test_resolve_from_environment(monkeypatch):
    monkeypatch.setenv("ONEC_OPS_IB_USER", "env-user")
    monkeypatch.setenv("ONEC_OPS_IB_PASSWORD", "env-secret")
    ns = build_parser().parse_args(["--ib", "/ib", "dump-cf", "--to", "base.cf"])
    _resolve_ib_auth(ns, IB_ACTIONS["dump-cf"])
    assert (ns.ib_user, ns.ib_password) == ("env-user", "env-secret")


def test_cli_overrides_environment(monkeypatch):
    monkeypatch.setenv("ONEC_OPS_IB_USER", "env-user")
    monkeypatch.setenv("ONEC_OPS_IB_PASSWORD", "env-secret")
    ns = build_parser().parse_args([
        "--ib", "/ib", "--ib-user", "cli-user", "--ib-password", "", "dump-cf", "--to", "base.cf",
    ])
    _resolve_ib_auth(ns, IB_ACTIONS["dump-cf"])
    assert (ns.ib_user, ns.ib_password) == ("cli-user", "")
    assert IB_ACTIONS["dump-cf"].ib_auth_args(ns) == ["/N", "cli-user"]


def test_resolve_password_without_user():
    ns = build_parser().parse_args(["--ib", "/ib", "--ib-password", "x", "dump-cf", "--to", "a.cf"])
    with pytest.raises(OneCOpsError, match="--ib-password требует --ib-user"):
        _resolve_ib_auth(ns, IB_ACTIONS["dump-cf"])


def test_resolve_environment_password_without_user(monkeypatch):
    monkeypatch.setenv("ONEC_OPS_IB_PASSWORD", "env-secret")
    ns = build_parser().parse_args(["--ib", "/ib", "dump-cf", "--to", "a.cf"])
    with pytest.raises(OneCOpsError, match="--ib-password требует --ib-user"):
        _resolve_ib_auth(ns, IB_ACTIONS["dump-cf"])


@pytest.mark.parametrize("option", ["--ib-user", "--ib-password"])
def test_create_ib_rejects_ib_auth(option, tmp_path):
    ns = build_parser().parse_args(["create-ib", "--type", "file", "--path", str(tmp_path), option, "x"])
    action = next(item for item in get_actions() if item.name == "create-ib")
    with pytest.raises(OneCOpsError, match="неприменимы к create-ib"):
        _resolve_ib_auth(ns, action)


def test_create_ib_ignores_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("ONEC_OPS_IB_USER", "env-user")
    monkeypatch.setenv("ONEC_OPS_IB_PASSWORD", "env-secret")
    ns = build_parser().parse_args(["create-ib", "--type", "file", "--path", str(tmp_path)])
    action = next(item for item in get_actions() if item.name == "create-ib")
    _resolve_ib_auth(ns, action)
    assert (ns.ib_user, ns.ib_password) == (None, None)


@pytest.mark.parametrize("name", ["open-designer", "open-enterprise"])
def test_legacy_gui_options_still_work(name, caplog):
    ns = build_parser().parse_args(["--ib", "/ib", name, "--user", "admin", "--password", "secret"])
    with caplog.at_level("WARNING"):
        _resolve_ib_auth(ns, IB_ACTIONS[name])
    assert (ns.ib_user, ns.ib_password) == ("admin", "secret")
    assert "устарели" in caplog.text


@pytest.mark.parametrize("name", ["open-designer", "open-enterprise"])
def test_legacy_and_new_same_value_allowed(name):
    ns = build_parser().parse_args([
        "--ib", "/ib", "--ib-user", "admin", name, "--user", "admin",
    ])
    _resolve_ib_auth(ns, IB_ACTIONS[name])
    assert ns.ib_user == "admin"


@pytest.mark.parametrize("name", ["open-designer", "open-enterprise"])
@pytest.mark.parametrize(
    ("new", "legacy", "message"),
    [
        (["--ib-user", "a"], ["--user", "b"], "--ib-user и --user"),
        (["--ib-user", "a", "--ib-password", "x"], ["--password", "y"], "--ib-password и --password"),
    ],
)
def test_legacy_and_new_conflict(name, new, legacy, message):
    ns = build_parser().parse_args(["--ib", "/ib", *new, name, *legacy])
    with pytest.raises(OneCOpsError, match=message):
        _resolve_ib_auth(ns, IB_ACTIONS[name])


def test_legacy_options_rejected_for_batch_commands(capsys):
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--ib", "/ib", "dump-cf", "--to", "a.cf", "--password", "x"])
    assert "unrecognized arguments" in capsys.readouterr().err


@pytest.mark.parametrize("dry_run", [False, True])
def test_cli_dump_cf_with_ib_user(dry_run, tmp_path, monkeypatch, mocker, caplog):
    monkeypatch.chdir(tmp_path)
    ib = tmp_path / "ib"
    ib.mkdir()
    (ib / "1Cv8.1CD").touch()
    platform = tmp_path / "1cv8"
    platform.touch()
    platform.chmod(0o755)
    run = mocker.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, "", ""))
    mocker.patch("scripts.onec_ops.check_environment")
    mocker.patch("scripts.lib.runner.shutil.which", return_value="/usr/bin/xvfb-run")
    argv = [
        "--platform", str(platform), "--ib", "ib", "--ib-user", "Пользователь2",
        "--ib-password", "secret", "dump-cf", "--to", "base.cf",
    ]
    if dry_run:
        argv.insert(0, "--dry-run")
    with caplog.at_level("INFO"):
        assert main(argv) == 0
    assert "secret" not in caplog.text
    assert "'/P', '***'" in caplog.text
    assert "'/N', 'Пользователь2'" in caplog.text
    if dry_run:
        run.assert_not_called()
    else:
        command = run.call_args.args[0]
        index = command.index("/F")
        assert command[index + 1:index + 6] == [str(ib), "/N", "Пользователь2", "/P", "secret"]


def test_cli_create_ib_with_ib_user_fails(tmp_path, caplog):
    assert main(["create-ib", "--type", "file", "--path", str(tmp_path / "ib"), "--ib-user", "x"]) == 1
    assert "неприменимы к create-ib" in caplog.text
