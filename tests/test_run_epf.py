"""Тесты run-epf и чтения журнала регистрации."""

from __future__ import annotations

import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from onec_ops.actions.run_epf import RunEpfAction
from onec_ops.cli import build_parser, main
from onec_ops.lib.eventlog import read_errors
from onec_ops.lib.exceptions import OneCOpsError
from onec_ops.lib.runner import RunContext
from onec_ops.lib.unsafe_protection import (
    conf_files,
    connection_string,
    disabled_by,
    read_patterns,
    suggested_line,
)

LOG_HEADER = "﻿1CV8LOG(ver 2.0)\r\n5583aacc-8ee0-40ea-8329-8fbf88013454\r\n\r\n"


def _record(stamp: str, severity: str, comment: str) -> str:
    comment = comment.replace('"', '""')
    return (
        f'{{{stamp},N,\r\n{{0,0}},2,1,2,1,11,{severity},"{comment}",0,\r\n'
        '{"U"},"",0,0,0,1,0,\r\n{0}\r\n},\r\n'
    )


def _write_log(path: Path, records: str) -> None:
    """Пишет журнал байтами: 1С хранит его с CRLF, текстовый режим Windows удвоил бы CR."""
    path.write_bytes((LOG_HEADER + records).encode("utf-8"))


def _out_file(command: list[str]) -> Path:
    return Path(command[command.index("/Out") + 1])


def _fake_run(returncode: int, out_text: str):
    """Имитирует 1С: пишет out_text в файл /Out в UTF-8 с BOM."""

    def run(command, **kwargs):
        _out_file(command).write_bytes(out_text.encode("utf-8-sig"))
        return subprocess.CompletedProcess(command, returncode, "", "")

    return run


@pytest.fixture
def ib(tmp_path):
    path = tmp_path / "ib"
    path.mkdir()
    (path / "1Cv8.1CD").touch()
    return path


@pytest.fixture
def epf(tmp_path):
    path = tmp_path / "Задача.epf"
    path.write_bytes(b"epf")
    return path


@pytest.fixture
def cli(tmp_path, ib, mocker):
    platform = tmp_path / "1cv8"
    platform.touch()
    platform.chmod(0o755)
    mocker.patch("onec_ops.cli.check_environment")
    mocker.patch("onec_ops.lib.runner.shutil.which", return_value="/usr/bin/xvfb-run")

    def run(*argv):
        return main(["--platform", str(platform), "--ib", str(ib), *argv])

    return run


def _ns(*argv, ib=None):
    ns = build_parser().parse_args(["run-epf", *argv])
    ns.ib = ib
    return ns


def test_param_and_c_alias():
    assert _ns("--epf", "a.epf", "--param", "x").param == "x"
    assert _ns("--epf", "a.epf", "--c", "y").param == "y"
    assert _ns("--epf", "a.epf").param is None


def test_validate_missing_epf(ib, tmp_path):
    with pytest.raises(OneCOpsError, match="не найден"):
        RunEpfAction().validate(_ns("--epf", str(tmp_path / "nope.epf"), ib=ib))


def test_validate_wrong_suffix(ib, tmp_path):
    report = tmp_path / "a.erf"
    report.touch()
    with pytest.raises(OneCOpsError, match=r"\.epf"):
        RunEpfAction().validate(_ns("--epf", str(report), ib=ib))


def test_validate_ok(ib, epf):
    RunEpfAction().validate(_ns("--epf", str(epf), ib=ib))


def test_build_args(ib, epf, tmp_path):
    ns = _ns("--epf", str(epf), "--param", "a b", ib=ib)
    ns.out_file = tmp_path / "out.txt"
    assert RunEpfAction().build_1c_args(ns, RunContext(tmp_path / "1cv8")) == [
        "ENTERPRISE",
        "/F",
        str(ib),
        "/DisableStartupDialogs",
        "/DisableStartupMessages",
        "/Execute",
        str(epf.resolve()),
        "/C",
        "a b",
        "/Out",
        str(tmp_path / "out.txt"),
    ]


def test_build_args_empty_param_kept(ib, epf, tmp_path):
    ns = _ns("--epf", str(epf), "--param", "", ib=ib)
    ns.out_file = None
    args = RunEpfAction().build_1c_args(ns, RunContext(tmp_path / "1cv8"))
    assert args[-2:] == ["/C", ""]
    assert "/Out" not in args


def test_success_prints_messages(cli, epf, mocker, capsys):
    run = mocker.patch("onec_ops.lib.runner._execute", side_effect=_fake_run(0, "Готово: 3"))

    assert cli("--ib-user", "Тест", "run-epf", "--epf", str(epf), "--c", "параметр") == 0
    command = run.call_args.args[0]
    assert "ENTERPRISE" in command
    assert command[command.index("/N") + 1] == "Тест"
    assert command[command.index("/C") + 1] == "параметр"
    assert not _out_file(command).exists()
    assert capsys.readouterr().out == "Готово: 3\n"


def test_success_without_messages(cli, epf, mocker, capsys):
    mocker.patch("onec_ops.lib.runner._execute", side_effect=_fake_run(0, ""))
    assert cli("--ib-user", "Тест", "run-epf", "--epf", str(epf)) == 0
    assert capsys.readouterr().out == ""


def test_default_timeout_is_short(cli, epf, mocker):
    run = mocker.patch("onec_ops.lib.runner._execute", side_effect=_fake_run(0, ""))
    cli("--ib-user", "Тест", "run-epf", "--epf", str(epf))
    assert run.call_args.kwargs["timeout"] == 120


def test_explicit_timeout(cli, epf, mocker):
    run = mocker.patch("onec_ops.lib.runner._execute", side_effect=_fake_run(0, ""))
    cli("--ib-user", "Тест", "--timeout", "30", "run-epf", "--epf", str(epf))
    assert run.call_args.kwargs["timeout"] == 30


def test_other_commands_keep_default_timeout(cli, tmp_path, mocker):
    run = mocker.patch(
        "onec_ops.lib.runner._execute", return_value=subprocess.CompletedProcess([], 0, "", "")
    )
    cli("dump-cf", "--to", str(tmp_path / "a.cf"))
    assert run.call_args.kwargs["timeout"] == 600


def test_timeout_adds_hint_and_log_errors(cli, ib, epf, mocker, caplog):
    def hang(command, **kwargs):
        _out_file(command).write_bytes("до ошибки".encode("utf-8-sig"))
        stamp = datetime.now().astimezone().strftime("%Y%m%d%H%M%S")
        log = ib / "1Cv8Log"
        log.mkdir()
        _write_log(
            log / "20261118000000.lgp",
            _record("20200101000000", "E", "старая ошибка")
            + _record(stamp, "I", "")
            + _record(stamp, "E", 'моя ошибка\r\n{Форма(4)}:ВызватьИсключение "моя ошибка";'),
        )
        raise subprocess.TimeoutExpired(command, 5)

    mocker.patch("onec_ops.lib.runner._execute", side_effect=hang)

    assert cli("--ib-user", "Тест", "--timeout", "5", "run-epf", "--epf", str(epf)) == 1
    error = next(r.getMessage() for r in caplog.records if r.name == "onec_ops.cli")
    assert "не завершилась за 5 секунд" in error
    assert "до ошибки" in error
    assert "Предупреждение безопасности" in error
    assert "DisableUnsafeActionProtection=" in error
    assert "ЗавершитьРаботуСистемы(Ложь)" in error
    assert 'моя ошибка\n{Форма(4)}:ВызватьИсключение "моя ошибка";' in error
    assert "старая ошибка" not in error


def test_nonzero_code_without_hang_hint(cli, epf, mocker, caplog):
    mocker.patch(
        "onec_ops.lib.runner._execute",
        side_effect=_fake_run(1, "Пользователь ИБ не идентифицирован"),
    )
    assert cli("--ib-user", "Тест", "run-epf", "--epf", str(epf)) == 1
    error = next(r.getMessage() for r in caplog.records if r.name == "onec_ops.cli")
    assert error == "1С завершилась с ненулевым кодом: 1\nПользователь ИБ не идентифицирован"


def test_out_file_removed_after_failure(cli, epf, mocker):
    run = mocker.patch("onec_ops.lib.runner._execute", side_effect=_fake_run(1, "x"))
    cli("--ib-user", "Тест", "run-epf", "--epf", str(epf))
    assert not _out_file(run.call_args.args[0]).exists()


def test_dry_run_does_not_start(cli, epf, mocker, capsys):
    run = mocker.patch("onec_ops.lib.runner._execute")
    assert cli("--ib-user", "Тест", "--dry-run", "run-epf", "--epf", str(epf)) == 0
    run.assert_not_called()
    assert capsys.readouterr().out == ""


def test_read_errors_no_log(ib):
    assert read_errors(ib, datetime.now().astimezone()) == []


def test_read_errors_skips_old_files(ib):
    log = ib / "1Cv8Log"
    log.mkdir()
    path = log / "old.lgp"
    _write_log(path, _record("29991231000000", "E", "x"))
    os.utime(path, (0, 0))
    assert read_errors(ib, datetime(2026, 1, 1, tzinfo=UTC)) == []


def test_read_errors_limit(ib):
    log = ib / "1Cv8Log"
    log.mkdir()
    records = "".join(_record("20260101000000", "E", f"ошибка {n}") for n in range(8))
    _write_log(log / "a.lgp", records)
    assert read_errors(ib, datetime(2025, 1, 1, tzinfo=UTC)) == [f"ошибка {n}" for n in range(3, 8)]


@pytest.fixture
def platform(tmp_path):
    path = tmp_path / "1cv8" / "x86_64" / "8.5.1.1343" / "1cv8"
    path.parent.mkdir(parents=True)
    path.touch()
    path.chmod(0o755)
    return path


def _write_conf(platform, text):
    conf = platform.parent / "conf" / "conf.cfg"
    conf.parent.mkdir(exist_ok=True)
    conf.write_text(text, encoding="utf-8")
    return conf


def _main(platform, ib, *argv):
    return main(["--platform", str(platform), "--ib", str(ib), *argv])


@pytest.fixture
def no_env(mocker):
    mocker.patch("onec_ops.cli.check_environment")
    mocker.patch("onec_ops.lib.runner.shutil.which", return_value="/usr/bin/xvfb-run")


def test_without_user_fails_fast(platform, ib, epf, mocker, no_env, caplog):
    run = mocker.patch("onec_ops.lib.runner._execute")
    assert _main(platform, ib, "run-epf", "--epf", str(epf)) == 1
    run.assert_not_called()
    error = next(r.getMessage() for r in caplog.records if r.name == "onec_ops.cli")
    assert "Без --ib-user" in error
    assert str(platform.parent / "conf" / "conf.cfg") in error
    assert suggested_line(ib.resolve()) in error


def test_without_user_dry_run_warns(platform, ib, epf, mocker, no_env, caplog):
    assert _main(platform, ib, "--dry-run", "run-epf", "--epf", str(epf)) == 0
    assert any(
        r.levelname == "WARNING" and "Без --ib-user" in r.getMessage() for r in caplog.records
    )


def test_without_user_skip_check(platform, ib, epf, mocker, no_env):
    run = mocker.patch("onec_ops.lib.runner._execute", side_effect=_fake_run(0, ""))
    assert _main(platform, ib, "run-epf", "--epf", str(epf), "--skip-protection-check") == 0
    assert "/N" not in run.call_args.args[0]


def test_without_user_conf_disables(platform, ib, epf, mocker, no_env):
    _write_conf(platform, "SystemLanguage=System\n" + suggested_line(ib.resolve()) + "\n")
    run = mocker.patch("onec_ops.lib.runner._execute", side_effect=_fake_run(0, "ok"))
    assert _main(platform, ib, "run-epf", "--epf", str(epf)) == 0
    assert run.called


def test_timeout_reports_conf(platform, ib, epf, mocker, no_env, caplog):
    conf = _write_conf(platform, suggested_line(ib.resolve()) + "\n")
    mocker.patch("onec_ops.lib.runner._execute", side_effect=subprocess.TimeoutExpired(["1cv8"], 5))
    assert _main(platform, ib, "run-epf", "--epf", str(epf)) == 1
    error = next(r.getMessage() for r in caplog.records if r.name == "onec_ops.cli")
    assert f"отключена в {conf}" in error


def test_conf_files(platform):
    assert conf_files(platform) == [
        platform.parent / "conf" / "conf.cfg",
        platform.parents[2] / "conf" / "conf.cfg",
    ]


def test_conf_files_short_path():
    assert conf_files(Path("1cv8")) == [Path("conf") / "conf.cfg"]


def test_read_patterns(tmp_path):
    conf = tmp_path / "conf.cfg"
    conf.write_text(
        "SystemLanguage=System\ndisableunsafeactionprotection= .*a.* ; .*b.*;\n",
        encoding="utf-8",
    )
    assert read_patterns([conf, tmp_path / "missing.cfg"]) == [(conf, ".*a.*"), (conf, ".*b.*")]


def test_suggested_line_matches_only_this_base(tmp_path):
    ib = tmp_path / "a b (т)" / "ib.1"
    pattern = suggested_line(ib).split("=", 1)[1]
    assert pattern.endswith("\\W.*")
    import re

    assert re.fullmatch(pattern, connection_string(ib))
    assert not re.fullmatch(pattern, connection_string(tmp_path / "a b (т)" / "ib.12"))
    assert not re.fullmatch(pattern, connection_string(tmp_path / "a b (т)" / "ib_1"))


def test_disabled_by_fullmatch_and_bad_pattern(platform, tmp_path):
    ib = tmp_path / "ib"
    conf = _write_conf(platform, f"DisableUnsafeActionProtection=([;.*{ib}")
    assert disabled_by(ib, platform) is None
    conf.write_text(f"DisableUnsafeActionProtection=.*{ib}", encoding="utf-8")
    assert disabled_by(ib, platform) is None
    conf.write_text("DisableUnsafeActionProtection=.*", encoding="utf-8")
    assert disabled_by(ib, platform) == conf
