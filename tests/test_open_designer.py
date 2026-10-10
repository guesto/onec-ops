"""Тесты GUI-действия open-designer."""

from __future__ import annotations

import argparse
import subprocess

import pytest

from scripts.actions.open_designer import OpenDesignerAction
from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext
from scripts.onec_ops import main


@pytest.fixture(autouse=True)
def gui_environment(monkeypatch, mocker):
    monkeypatch.setattr("scripts.actions.open_designer.sys.platform", "linux")
    monkeypatch.setenv("DISPLAY", ":99")
    mocker.patch("scripts.actions.open_designer._verify_display", return_value=True)
    mocker.patch("scripts.actions.open_designer._detect_codex_sandbox", return_value=False)
    run = mocker.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, "", ""))
    popen = mocker.patch("subprocess.Popen", return_value=mocker.Mock(pid=1234))
    return run, popen


@pytest.fixture
def ns(tmp_path):
    ib = tmp_path / "ib"
    ib.mkdir()
    (ib / "1Cv8.1CD").touch()
    return argparse.Namespace(
        ib=ib,
        user=None,
        password=None,
        no_wait=False,
        dry_run=False,
        execute=None,
        c=None,
    )


@pytest.fixture
def ctx(tmp_path):
    platform = tmp_path / "1cv8"
    platform.touch()
    platform.chmod(0o755)
    return RunContext(platform, requires_gui=True)


def test_validate_missing_ib(ns):
    ns.ib = None
    with pytest.raises(OneCOpsError, match="--ib"):
        OpenDesignerAction().validate(ns)


def test_validate_ib_without_database_file(ns):
    (ns.ib / "1Cv8.1CD").unlink()
    with pytest.raises(OneCOpsError, match="1Cv8.1CD"):
        OpenDesignerAction().validate(ns)


def test_validate_missing_display(ns, monkeypatch):
    monkeypatch.delenv("DISPLAY", raising=False)
    with pytest.raises(OneCOpsError, match="реальный DISPLAY"):
        OpenDesignerAction().validate(ns)


def test_validate_display_not_working(ns, mocker):
    verify = mocker.patch("scripts.actions.open_designer._verify_display", return_value=False)
    with pytest.raises(OneCOpsError, match="X-сервер.*не отвечает"):
        OpenDesignerAction().validate(ns)
    verify.assert_called_once_with(":99")


def test_validate_sandbox_detected(ns, mocker):
    mocker.patch("scripts.actions.open_designer._detect_codex_sandbox", return_value=True)
    with pytest.raises(OneCOpsError, match="sandbox-режиме Codex"):
        OpenDesignerAction().validate(ns)


def test_validate_ok(ns):
    OpenDesignerAction().validate(ns)


def test_validate_windows_without_display(ns, monkeypatch, mocker):
    monkeypatch.setattr("scripts.actions.open_designer.sys.platform", "win32")
    monkeypatch.delenv("DISPLAY", raising=False)
    verify = mocker.patch("scripts.actions.open_designer._verify_display")
    sandbox = mocker.patch("scripts.actions.open_designer._detect_codex_sandbox")
    OpenDesignerAction().validate(ns)
    verify.assert_not_called()
    sandbox.assert_not_called()


def test_build_1c_args_base(ns, ctx):
    assert OpenDesignerAction().build_1c_args(ns, ctx) == ["DESIGNER", "/F", str(ns.ib)]


def test_build_1c_args_with_user_password(ns, ctx):
    ns.user = "Admin"
    ns.password = "secret"
    assert OpenDesignerAction().build_1c_args(ns, ctx) == [
        "DESIGNER",
        "/F",
        str(ns.ib),
        "/N",
        "Admin",
        "/P",
        "secret",
    ]


def test_build_1c_args_with_no_wait(ns, ctx, mocker):
    ns.no_wait = True
    action = OpenDesignerAction()
    args = action.build_1c_args(ns, ctx)
    popen = mocker.patch(
        "scripts.actions.open_designer.run_1c_popen", return_value=mocker.Mock(pid=1234)
    )
    run = mocker.patch("scripts.actions.open_designer.run_1c")
    action.pre_run(ns, ctx)
    assert args == ["DESIGNER", "/F", str(ns.ib)]
    popen.assert_called_once_with(args, ctx)
    run.assert_not_called()


@pytest.mark.parametrize("no_wait", [False, True])
def test_cli_starts_exactly_once(ns, ctx, no_wait, gui_environment, mocker, caplog):
    run, popen = gui_environment
    mocker.patch("scripts.onec_ops.check_environment")
    argv = [
        "--platform",
        str(ctx.platform_path),
        "--ib",
        str(ns.ib),
        "open-designer",
        "--user",
        "Admin",
        "--password",
        "secret",
    ]
    if no_wait:
        argv += ["--no-wait"]
    with caplog.at_level("INFO"):
        assert main(argv) == 0
    expected = [str(ctx.platform_path), "DESIGNER", "/F", str(ns.ib), "/N", "Admin", "/P", "secret"]
    if no_wait:
        popen.assert_called_once_with(
            expected, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        run.assert_not_called()
        assert "1234" in caplog.text
    else:
        run.assert_called_once()
        assert run.call_args.args[0] == expected
        popen.assert_not_called()
    assert "secret" not in caplog.text
    assert "***" in caplog.text


@pytest.mark.parametrize("no_wait", [False, True])
def test_cli_dry_run_without_display_or_xvfb(
    ns, ctx, no_wait, gui_environment, monkeypatch, mocker, caplog
):
    run, popen = gui_environment
    monkeypatch.delenv("DISPLAY", raising=False)
    mocker.patch("scripts.lib.runner.shutil.which", return_value=None)
    verify = mocker.patch("scripts.actions.open_designer._verify_display")
    sandbox = mocker.patch("scripts.actions.open_designer._detect_codex_sandbox", return_value=True)
    argv = [
        "--platform",
        str(ctx.platform_path),
        "--ib",
        str(ns.ib),
        "--dry-run",
        "open-designer",
    ]
    if no_wait:
        argv += ["--no-wait"]
    with caplog.at_level("INFO"):
        assert main(argv) == 0
    run.assert_not_called()
    popen.assert_not_called()
    verify.assert_not_called()
    sandbox.assert_not_called()
    assert "Dry-run" in caplog.text
    assert "xvfb-run" not in caplog.text
    assert "DESIGNER" in caplog.text


def test_cli_missing_display_prevents_launch(ns, ctx, gui_environment, monkeypatch, mocker, caplog):
    run, popen = gui_environment
    monkeypatch.delenv("DISPLAY", raising=False)
    environment = mocker.patch("scripts.onec_ops.check_environment")
    assert main(["--platform", str(ctx.platform_path), "--ib", str(ns.ib), "open-designer"]) == 1
    assert "реальный DISPLAY" in caplog.text
    environment.assert_not_called()
    run.assert_not_called()
    popen.assert_not_called()
