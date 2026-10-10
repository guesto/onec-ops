"""Тесты запуска 1С."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.lib.exceptions import OneCFailed, XvfbNotAvailable
from scripts.lib.runner import RunContext, build_command, run_1c, run_1c_popen


def _platform(tmp_path: Path) -> Path:
    platform = tmp_path / "1cv8"
    platform.touch()
    platform.chmod(0o755)
    return platform


def test_build_command_uses_platform_directly_on_windows(tmp_path, monkeypatch):
    platform = _platform(tmp_path)
    monkeypatch.setattr("scripts.lib.runner.sys.platform", "win32")

    assert build_command(["DESIGNER"], RunContext(platform)) == [str(platform), "DESIGNER"]


def test_build_command_uses_platform_with_display(tmp_path, monkeypatch):
    platform = _platform(tmp_path)
    monkeypatch.setattr("scripts.lib.runner.sys.platform", "linux")
    monkeypatch.setenv("DISPLAY", ":99")

    assert build_command(["DESIGNER"], RunContext(platform)) == [str(platform), "DESIGNER"]


def test_build_command_uses_xvfb_without_display(tmp_path, monkeypatch):
    platform = _platform(tmp_path)
    monkeypatch.setattr("scripts.lib.runner.sys.platform", "linux")
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.setattr("scripts.lib.runner.shutil.which", lambda name: "/usr/bin/xvfb-run")

    assert build_command(["DESIGNER"], RunContext(platform)) == [
        "xvfb-run",
        "-a",
        "-s",
        "-nolisten unix",
        str(platform),
        "DESIGNER",
    ]


def test_build_command_fails_without_display_or_xvfb(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.lib.runner.sys.platform", "linux")
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.setattr("scripts.lib.runner.shutil.which", lambda name: None)

    with pytest.raises(XvfbNotAvailable):
        build_command(["DESIGNER"], RunContext(_platform(tmp_path)))


def test_dry_run_does_not_start_subprocess(tmp_path, monkeypatch, mocker):
    monkeypatch.setattr("scripts.lib.runner.sys.platform", "win32")
    run_mock = mocker.patch("subprocess.run")

    result = run_1c(["DESIGNER"], RunContext(_platform(tmp_path), dry_run=True))

    run_mock.assert_not_called()
    assert result.returncode == 0


def test_timeout_becomes_onec_failed(tmp_path, monkeypatch, mocker):
    monkeypatch.setattr("scripts.lib.runner.sys.platform", "win32")
    mocker.patch("subprocess.run", side_effect=subprocess.TimeoutExpired(["1cv8"], 10))

    with pytest.raises(OneCFailed) as error:
        run_1c(["DESIGNER"], RunContext(_platform(tmp_path), timeout=10))

    assert error.value.returncode == -1


def test_password_is_masked_in_logs(tmp_path, monkeypatch, mocker, caplog):
    monkeypatch.setattr("scripts.lib.runner.sys.platform", "win32")
    mocker.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, "", ""))

    with caplog.at_level("INFO"):
        run_1c(
            ["DESIGNER", "/P", "secret", "/ConfigurationRepositoryP", "repo-secret"],
            RunContext(_platform(tmp_path)),
        )

    assert "secret" not in caplog.text
    assert "repo-secret" not in caplog.text
    assert "***" in caplog.text


def test_popen_when_no_wait(tmp_path, monkeypatch, mocker):
    monkeypatch.setattr("scripts.lib.runner.sys.platform", "win32")
    platform = _platform(tmp_path)
    process = mocker.Mock(pid=1234)
    popen = mocker.patch("subprocess.Popen", return_value=process)
    run = mocker.patch("subprocess.run")
    assert run_1c_popen(["DESIGNER"], RunContext(platform)) is process
    popen.assert_called_once_with(
        [str(platform), "DESIGNER"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    run.assert_not_called()


def test_popen_dry_run_does_not_start_process(tmp_path, monkeypatch, mocker):
    monkeypatch.setattr("scripts.lib.runner.sys.platform", "win32")
    popen = mocker.patch("subprocess.Popen")
    assert run_1c_popen(["DESIGNER"], RunContext(_platform(tmp_path), dry_run=True)) is None
    popen.assert_not_called()


def test_popen_password_is_masked_in_logs(tmp_path, monkeypatch, mocker, caplog):
    monkeypatch.setattr("scripts.lib.runner.sys.platform", "win32")
    mocker.patch("subprocess.Popen", return_value=mocker.Mock(pid=1234))
    with caplog.at_level("INFO"):
        run_1c_popen(["DESIGNER", "/P", "secret"], RunContext(_platform(tmp_path)))
    assert "secret" not in caplog.text
    assert "***" in caplog.text


def test_popen_os_error_becomes_onec_failed(tmp_path, monkeypatch, mocker):
    monkeypatch.setattr("scripts.lib.runner.sys.platform", "win32")
    mocker.patch("subprocess.Popen", side_effect=OSError("launch failed"))
    with pytest.raises(OneCFailed, match="Не удалось запустить 1С") as error:
        run_1c_popen(["DESIGNER"], RunContext(_platform(tmp_path)))
    assert error.value.returncode == -1


def test_gui_command_dry_run_does_not_use_xvfb(tmp_path, monkeypatch, mocker):
    monkeypatch.setattr("scripts.lib.runner.sys.platform", "linux")
    monkeypatch.delenv("DISPLAY", raising=False)
    which = mocker.patch("scripts.lib.runner.shutil.which")
    platform = _platform(tmp_path)
    assert build_command(["DESIGNER"], RunContext(platform, requires_gui=True, dry_run=True)) == [
        str(platform),
        "DESIGNER",
    ]
    which.assert_not_called()
