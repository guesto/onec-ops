"""Тесты проверки DISPLAY и эвристики sandbox без реальных X-серверов."""

from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest

from scripts.lib.runner import _detect_codex_sandbox, _verify_display


@pytest.fixture(autouse=True)
def processes(mocker):
    mocker.patch("subprocess.Popen")
    run = mocker.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0))
    mocker.patch("scripts.lib.runner.shutil.which", return_value="/usr/bin/xdpyinfo")
    return run


def test_verify_display_ok(processes):
    assert _verify_display(":99") is True
    processes.assert_called_once_with(
        ["/usr/bin/xdpyinfo", "-display", ":99"],
        capture_output=True,
        timeout=5,
        check=False,
    )


def test_verify_display_fails(processes):
    processes.return_value = subprocess.CompletedProcess([], 1)
    assert _verify_display(":99") is False


def test_verify_display_no_xdpyinfo(processes, mocker, caplog):
    mocker.patch("scripts.lib.runner.shutil.which", return_value=None)
    with caplog.at_level("WARNING"):
        assert _verify_display(":99") is True
    processes.assert_not_called()
    assert "проверка DISPLAY пропущена" in caplog.text


@pytest.mark.parametrize(
    "error", [subprocess.TimeoutExpired(["xdpyinfo"], 5), OSError("unavailable")]
)
def test_verify_display_error(processes, error):
    processes.side_effect = error
    assert _verify_display(":99") is False


def test_detect_sandbox_non_root_x11_directory(mocker):
    mocker.patch("scripts.lib.runner.Path.exists", return_value=True)
    mocker.patch("scripts.lib.runner.Path.stat", return_value=SimpleNamespace(st_uid=65534))
    assert _detect_codex_sandbox() is True


def test_detect_sandbox_root_x11_directory(mocker):
    mocker.patch("scripts.lib.runner.Path.exists", return_value=True)
    mocker.patch("scripts.lib.runner.Path.stat", return_value=SimpleNamespace(st_uid=0))
    assert _detect_codex_sandbox() is False


def test_detect_sandbox_missing_x11_directory(mocker):
    mocker.patch("scripts.lib.runner.Path.exists", return_value=False)
    stat = mocker.patch("scripts.lib.runner.Path.stat")
    assert _detect_codex_sandbox() is False
    stat.assert_not_called()


def test_detect_sandbox_stat_error(mocker):
    mocker.patch("scripts.lib.runner.Path.exists", return_value=True)
    mocker.patch("scripts.lib.runner.Path.stat", side_effect=OSError("unavailable"))
    assert _detect_codex_sandbox() is False
