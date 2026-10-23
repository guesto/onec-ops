"""Тесты запуска 1С."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from scripts.lib.exceptions import OneCFailed, PlatformNotFound, XvfbNotAvailable
from scripts.lib.runner import RunContext, _execute, build_command, run_1c, run_1c_popen


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
    run_mock = mocker.patch("scripts.lib.runner._execute")

    result = run_1c(["DESIGNER"], RunContext(_platform(tmp_path), dry_run=True))

    run_mock.assert_not_called()
    assert result.returncode == 0


def test_timeout_becomes_onec_failed(tmp_path, monkeypatch, mocker):
    monkeypatch.setattr("scripts.lib.runner.sys.platform", "win32")
    mocker.patch("scripts.lib.runner._execute", side_effect=subprocess.TimeoutExpired(["1cv8"], 10))

    with pytest.raises(OneCFailed) as error:
        run_1c(["DESIGNER"], RunContext(_platform(tmp_path), timeout=10))

    assert error.value.returncode == -1


def test_password_is_masked_in_logs(tmp_path, monkeypatch, mocker, caplog):
    monkeypatch.setattr("scripts.lib.runner.sys.platform", "win32")
    mocker.patch("scripts.lib.runner._execute", return_value=subprocess.CompletedProcess([], 0, "", ""))

    with caplog.at_level("INFO"):
        run_1c(
            ["DESIGNER", "/P", "secret", "/ConfigurationRepositoryP", "repo-secret"],
            RunContext(_platform(tmp_path)),
        )

    assert "secret" not in caplog.text
    assert "repo-secret" not in caplog.text
    assert "***" in caplog.text


def test_repo_user_password_is_masked_in_logs(tmp_path, monkeypatch, mocker, caplog):
    monkeypatch.setattr("scripts.lib.runner.sys.platform", "win32")
    mocker.patch("scripts.lib.runner._execute", return_value=subprocess.CompletedProcess([], 0, "", ""))

    with caplog.at_level("INFO"):
        run_1c(
            ["DESIGNER", "/ConfigurationRepositoryAddUser", "-User", "dev", "-Pwd", "user-secret"],
            RunContext(_platform(tmp_path)),
        )

    assert "user-secret" not in caplog.text
    assert "-User', 'dev'" in caplog.text
    assert "***" in caplog.text


def test_popen_when_no_wait(tmp_path, monkeypatch, mocker):
    monkeypatch.setattr("scripts.lib.runner.sys.platform", "win32")
    platform = _platform(tmp_path)
    process = mocker.Mock(pid=1234)
    popen = mocker.patch("subprocess.Popen", return_value=process)
    run = mocker.patch("scripts.lib.runner._execute")
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


def _fake_run(returncode: int, out_text: str | None = None):
    """Имитирует 1С: пишет out_text в файл /Out (последний аргумент) в UTF-8 с BOM."""
    def run(command, **kwargs):
        if out_text is not None:
            out_path = Path(command[-1])
            out_path.write_bytes(out_text.encode("utf-8-sig"))
        return subprocess.CompletedProcess(command, returncode, "", "")
    return run


@pytest.mark.parametrize("mode", ["DESIGNER", "CREATEINFOBASE"])
def test_out_file_added_and_removed(tmp_path, monkeypatch, mocker, mode):
    monkeypatch.setattr("scripts.lib.runner.sys.platform", "win32")
    run = mocker.patch("scripts.lib.runner._execute", side_effect=_fake_run(0, ""))

    run_1c([mode, "/F", "ib"], RunContext(_platform(tmp_path)))

    command = run.call_args.args[0]
    assert command[1:4] == [mode, "/F", "ib"]
    assert command[-2] == "/Out"
    assert not Path(command[-1]).exists()


@pytest.mark.parametrize(
    ("args", "ctx_kwargs"),
    [
        (["DESIGNER"], {"requires_gui": True}),
        (["ENTERPRISE"], {}),
        ([], {}),
    ],
)
def test_out_file_not_added(tmp_path, monkeypatch, mocker, args, ctx_kwargs):
    monkeypatch.setattr("scripts.lib.runner.sys.platform", "win32")
    platform = _platform(tmp_path)
    run = mocker.patch("scripts.lib.runner._execute", return_value=subprocess.CompletedProcess([], 0, "", ""))

    run_1c(args, RunContext(platform, **ctx_kwargs))

    assert run.call_args.args[0] == [str(platform), *args]


def test_dry_run_does_not_add_out_file(tmp_path, monkeypatch, mocker):
    monkeypatch.setattr("scripts.lib.runner.sys.platform", "win32")
    mkstemp = mocker.patch("scripts.lib.runner.tempfile.mkstemp")

    result = run_1c(["DESIGNER"], RunContext(_platform(tmp_path), dry_run=True))

    mkstemp.assert_not_called()
    assert "/Out" not in result.args


def test_existing_out_is_read_and_kept(tmp_path, monkeypatch, mocker):
    monkeypatch.setattr("scripts.lib.runner.sys.platform", "win32")
    platform = _platform(tmp_path)
    out_file = tmp_path / "out.txt"
    mocker.patch("scripts.lib.runner._execute", side_effect=_fake_run(1, "Ошибка из /out"))

    with pytest.raises(OneCFailed, match="Ошибка из /out"):
        run_1c(["DESIGNER", "/out", str(out_file)], RunContext(platform))

    assert out_file.exists()


def test_out_text_in_error_and_log(tmp_path, monkeypatch, mocker, caplog):
    monkeypatch.setattr("scripts.lib.runner.sys.platform", "win32")
    message = "Пользователь хранилища конфигурации с именем 'user2' уже существует"
    run = mocker.patch("scripts.lib.runner._execute", side_effect=_fake_run(1, message + "\r\n"))

    with caplog.at_level("INFO"), pytest.raises(OneCFailed) as error:
        run_1c(["DESIGNER"], RunContext(_platform(tmp_path)))

    assert str(error.value) == f"1С завершилась с ненулевым кодом: 1\n{message}"
    assert "﻿" not in str(error.value)
    assert message in caplog.text
    assert not Path(run.call_args.args[0][-1]).exists()


def test_empty_out_keeps_plain_error(tmp_path, monkeypatch, mocker):
    monkeypatch.setattr("scripts.lib.runner.sys.platform", "win32")
    mocker.patch("scripts.lib.runner._execute", side_effect=_fake_run(1, ""))

    with pytest.raises(OneCFailed) as error:
        run_1c(["DESIGNER"], RunContext(_platform(tmp_path)))

    assert str(error.value) == "1С завершилась с ненулевым кодом: 1"


def test_missing_out_file_is_not_an_error(tmp_path, monkeypatch, mocker):
    monkeypatch.setattr("scripts.lib.runner.sys.platform", "win32")

    def run(command, **kwargs):
        Path(command[-1]).unlink()
        return subprocess.CompletedProcess(command, 1, "", "")

    mocker.patch("scripts.lib.runner._execute", side_effect=run)

    with pytest.raises(OneCFailed) as error:
        run_1c(["DESIGNER"], RunContext(_platform(tmp_path)))

    assert str(error.value) == "1С завершилась с ненулевым кодом: 1"


def test_timeout_includes_out_text_and_removes_file(tmp_path, monkeypatch, mocker):
    monkeypatch.setattr("scripts.lib.runner.sys.platform", "win32")
    paths = []

    def run(command, **kwargs):
        paths.append(Path(command[-1]))
        paths[0].write_bytes("Ожидание блокировки".encode("utf-8-sig"))
        raise subprocess.TimeoutExpired(command, 10)

    mocker.patch("scripts.lib.runner._execute", side_effect=run)

    with pytest.raises(OneCFailed, match="Ожидание блокировки"):
        run_1c(["DESIGNER"], RunContext(_platform(tmp_path), timeout=10))

    assert not paths[0].exists()


def test_out_file_removed_when_platform_missing(tmp_path, monkeypatch, mocker):
    monkeypatch.setattr("scripts.lib.runner.sys.platform", "win32")
    created = []
    real_mkstemp = __import__("tempfile").mkstemp

    def mkstemp(**kwargs):
        fd, name = real_mkstemp(dir=tmp_path, **kwargs)
        created.append(Path(name))
        return fd, name

    mocker.patch("scripts.lib.runner.tempfile.mkstemp", side_effect=mkstemp)

    with pytest.raises(PlatformNotFound):
        run_1c(["DESIGNER"], RunContext(tmp_path / "missing"))

    assert created and not created[0].exists()


def test_result_contains_out_text(tmp_path, monkeypatch, mocker):
    monkeypatch.setattr("scripts.lib.runner.sys.platform", "win32")
    mocker.patch("scripts.lib.runner._execute", side_effect=_fake_run(0, "onec\r\nДругое\r\n"))

    result = run_1c(["DESIGNER"], RunContext(_platform(tmp_path)))

    assert result.out_text == "onec\nДругое"
    assert result.returncode == 0


def test_dry_run_result_has_empty_out_text(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.lib.runner.sys.platform", "win32")

    result = run_1c(["DESIGNER"], RunContext(_platform(tmp_path), dry_run=True))

    assert result.out_text == ""


# --- группа процессов (v0.8.1) ------------------------------------------------

posix_only = pytest.mark.skipif(sys.platform == "win32", reason="группы процессов POSIX")


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    # Зомби ещё виден kill(0), но уже не работает.
    try:
        with open(f"/proc/{pid}/stat", encoding="utf-8") as stat:
            return stat.read().split(")")[-1].split()[0] != "Z"
    except OSError:
        return True


def _script_with_grandchild(tmp_path: Path) -> tuple[Path, Path]:
    """Скрипт запускает «внука» в фоне (как xvfb-run запускает Xvfb и 1cv8) и ждёт."""
    pid_file = tmp_path / "grandchild.pid"
    script = tmp_path / "fake1cv8"
    script.write_text(f"#!/bin/sh\nsleep 60 &\necho $! > {pid_file}\nwait\n")
    script.chmod(0o755)
    return script, pid_file


def _wait_pid_file(pid_file: Path) -> int:
    for _ in range(100):
        if pid_file.exists() and pid_file.read_text().strip():
            return int(pid_file.read_text())
        time.sleep(0.02)
    raise AssertionError("скрипт не записал PID внука")


def test_execute_returns_output(tmp_path):
    result = _execute([sys.executable, "-c", "import sys; print('out'); print('err', file=sys.stderr); sys.exit(3)"], timeout=10)
    assert (result.returncode, result.stdout.strip(), result.stderr.strip()) == (3, "out", "err")


@posix_only
def test_execute_timeout_kills_process_group(tmp_path):
    script, pid_file = _script_with_grandchild(tmp_path)
    with pytest.raises(subprocess.TimeoutExpired):
        _execute([str(script)], timeout=1)
    grandchild = _wait_pid_file(pid_file)
    time.sleep(0.1)
    assert not _alive(grandchild)


@posix_only
def test_execute_interrupt_kills_process_group(tmp_path, mocker):
    script, pid_file = _script_with_grandchild(tmp_path)
    real_communicate = subprocess.Popen.communicate

    def interrupted(self, *args, **kwargs):
        _wait_pid_file(pid_file)
        raise KeyboardInterrupt

    mocker.patch.object(subprocess.Popen, "communicate", interrupted)
    with pytest.raises(KeyboardInterrupt):
        _execute([str(script)], timeout=10)
    mocker.patch.object(subprocess.Popen, "communicate", real_communicate)
    time.sleep(0.1)
    assert not _alive(int(pid_file.read_text()))


@posix_only
def test_run_1c_timeout_leaves_no_processes(tmp_path, monkeypatch):
    script, pid_file = _script_with_grandchild(tmp_path)
    monkeypatch.setenv("DISPLAY", ":0")
    with pytest.raises(OneCFailed, match="не завершилась за 1 секунд"):
        run_1c(["DESIGNER"], RunContext(script, timeout=1))
    time.sleep(0.1)
    assert not _alive(_wait_pid_file(pid_file))


def test_run_1c_os_error_becomes_onec_failed(tmp_path, monkeypatch, mocker):
    monkeypatch.setattr("scripts.lib.runner.sys.platform", "win32")
    mocker.patch("scripts.lib.runner._execute", side_effect=OSError("Exec format error"))
    with pytest.raises(OneCFailed, match="Не удалось запустить 1С: Exec format error"):
        run_1c(["DESIGNER"], RunContext(_platform(tmp_path)))


def test_kill_process_group_windows(monkeypatch, mocker):
    from scripts.lib.runner import _kill_process_group

    monkeypatch.setattr("scripts.lib.runner.sys.platform", "win32")
    process = mocker.Mock(pid=4321)
    killpg = mocker.patch("scripts.lib.runner.os.killpg", create=True)
    _kill_process_group(process)
    process.kill.assert_called_once_with()
    killpg.assert_not_called()


def test_kill_process_group_already_gone(monkeypatch, mocker):
    from scripts.lib.runner import _kill_process_group

    monkeypatch.setattr("scripts.lib.runner.sys.platform", "linux")
    mocker.patch("scripts.lib.runner.os.killpg", create=True, side_effect=ProcessLookupError)
    _kill_process_group(mocker.Mock(pid=4321))


@posix_only
def test_execute_kills_children_ignoring_sigterm(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.lib.runner._TERMINATE_GRACE", 0.5)
    pid_file = tmp_path / "grandchild.pid"
    script = tmp_path / "stubborn1cv8"
    script.write_text(
        "#!/bin/sh\n"
        f"sh -c 'trap \"\" TERM; echo $$ > {pid_file}; while :; do sleep 1; done' &\n"
        "wait\n"
    )
    script.chmod(0o755)
    with pytest.raises(subprocess.TimeoutExpired):
        _execute([str(script)], timeout=1)
    time.sleep(0.2)
    assert not _alive(_wait_pid_file(pid_file))
