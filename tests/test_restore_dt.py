"""Тесты восстановления базы из .dt и подтверждения перезаписи."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import pytest

from scripts.actions.restore_dt import RestoreDtAction
from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext
from scripts.onec_ops import build_parser, main


@pytest.fixture(autouse=True)
def subprocess_mock(mocker):
    mocker.patch("subprocess.Popen")
    return mocker.patch("scripts.lib.runner._execute", return_value=subprocess.CompletedProcess([], 0, "", ""))


@pytest.fixture
def ns(tmp_path):
    ib = tmp_path / "ib"
    ib.mkdir()
    (ib / "1Cv8.1CD").write_bytes(b"existing database")
    source = tmp_path / "base.dt"
    source.write_bytes(b"backup")
    return argparse.Namespace(ib=ib, from_=source, force=False, yes=False)


@pytest.fixture
def ctx(tmp_path):
    platform = tmp_path / "1cv8"
    platform.touch()
    platform.chmod(0o755)
    return RunContext(platform)


@pytest.fixture
def stdin(mocker):
    stream = mocker.patch("scripts.actions.restore_dt.sys.stdin")
    stream.isatty.return_value = True
    stream.readline.return_value = "Y\n"
    return stream


def test_validate_missing_ib(ns):
    ns.ib = None
    with pytest.raises(OneCOpsError, match="--ib"):
        RestoreDtAction().validate(ns)


def test_validate_ib_not_exists(ns):
    ns.ib = ns.ib / "missing"
    with pytest.raises(OneCOpsError, match="1Cv8.1CD"):
        RestoreDtAction().validate(ns)


def test_validate_ib_without_database(ns):
    (ns.ib / "1Cv8.1CD").unlink()
    with pytest.raises(OneCOpsError, match="1Cv8.1CD"):
        RestoreDtAction().validate(ns)


def test_validate_missing_from(ns):
    ns.from_ = None
    with pytest.raises(OneCOpsError, match="--from"):
        RestoreDtAction().validate(ns)


def test_parser_requires_from(ns):
    with pytest.raises(SystemExit) as error:
        build_parser().parse_args(["restore-dt", "--ib", str(ns.ib)])
    assert error.value.code == 2


def test_validate_from_not_exists(ns):
    ns.from_.unlink()
    with pytest.raises(OneCOpsError, match="не существует"):
        RestoreDtAction().validate(ns)


def test_validate_from_empty(ns):
    ns.from_.write_bytes(b"")
    with pytest.raises(OneCOpsError, match="пустой"):
        RestoreDtAction().validate(ns)


def test_validate_from_is_directory(ns):
    ns.from_.unlink()
    ns.from_.mkdir()
    with pytest.raises(OneCOpsError, match="должен быть файлом"):
        RestoreDtAction().validate(ns)


def test_validate_from_wrong_suffix(ns):
    ns.from_ = ns.from_.rename(ns.from_.with_suffix(".bin"))
    with pytest.raises(OneCOpsError, match="должен иметь расширение .dt"):
        RestoreDtAction().validate(ns)


@pytest.mark.parametrize("suffix", [".dt", ".DT"])
def test_validate_ok(ns, suffix, stdin):
    ns.from_ = ns.from_.rename(ns.from_.with_suffix(suffix))
    RestoreDtAction().validate(ns)
    stdin.readline.assert_not_called()


def test_build_1c_args_with_absolute_paths(ns, ctx, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ns.ib = Path("ib")
    ns.from_ = Path("base.dt")
    action = RestoreDtAction()
    action.resolve_paths(ns)
    assert ns.ib == tmp_path / "ib"
    assert ns.from_ == tmp_path / "base.dt"
    assert action.build_1c_args(ns, ctx) == [
        "DESIGNER",
        "/F",
        str(tmp_path / "ib"),
        "/DisableStartupDialogs",
        "/RestoreIB",
        str(tmp_path / "base.dt"),
    ]


@pytest.mark.parametrize("force", [False, True])
def test_pre_run_warns_and_confirms(ns, ctx, stdin, caplog, capsys, force):
    ns.force = force
    with caplog.at_level("WARNING"):
        RestoreDtAction().pre_run(ns, ctx)
    assert "будут перезаписаны" in caplog.text
    assert str(ns.ib) in caplog.text
    assert "введите Y" in capsys.readouterr().err
    stdin.readline.assert_called_once_with()
    assert (ns.ib / "1Cv8.1CD").read_bytes() == b"existing database"
    assert ns.from_.read_bytes() == b"backup"


@pytest.mark.parametrize("answer", ["n\n", "\n", "", "unexpected\n"])
def test_pre_run_rejects_without_explicit_confirmation(ns, ctx, stdin, answer):
    stdin.readline.return_value = answer
    with pytest.raises(OneCOpsError, match="Отменено"):
        RestoreDtAction().pre_run(ns, ctx)


def test_pre_run_force_yes_skips_prompt(ns, ctx, stdin, caplog):
    ns.force = ns.yes = True
    stdin.isatty.return_value = False
    with caplog.at_level("WARNING"):
        RestoreDtAction().pre_run(ns, ctx)
    assert "--force --yes" in caplog.text
    stdin.isatty.assert_not_called()
    stdin.readline.assert_not_called()


def test_pre_run_yes_without_force_still_confirms(ns, ctx, stdin):
    ns.yes = True
    RestoreDtAction().pre_run(ns, ctx)
    stdin.readline.assert_called_once_with()


@pytest.mark.parametrize("force", [False, True])
def test_pre_run_non_tty_requires_force_yes(ns, ctx, stdin, force):
    ns.force = force
    stdin.isatty.return_value = False
    with pytest.raises(OneCOpsError, match="--force --yes"):
        RestoreDtAction().pre_run(ns, ctx)
    stdin.readline.assert_not_called()


@pytest.mark.parametrize("dry_run", [False, True])
def test_cli_runs_with_mocked_subprocess(
    ns, ctx, subprocess_mock, mocker, stdin, caplog, dry_run
):
    mocker.patch("scripts.onec_ops.check_environment")
    mocker.patch("scripts.lib.runner.shutil.which", return_value="/usr/bin/xvfb-run")
    argv = [
        "--platform", str(ctx.platform_path), "--ib", str(ns.ib),
        "restore-dt", "--from", str(ns.from_), "--force", "--yes",
    ]
    if dry_run:
        argv += ["--dry-run"]
    with caplog.at_level("INFO"):
        assert main(argv) == 0
    stdin.readline.assert_not_called()
    assert (ns.ib / "1Cv8.1CD").read_bytes() == b"existing database"
    if dry_run:
        subprocess_mock.assert_not_called()
        assert "Dry-run" in caplog.text
        assert "/RestoreIB" in caplog.text
    else:
        subprocess_mock.assert_called_once()
        expected = RestoreDtAction().build_1c_args(ns, ctx)
        command = subprocess_mock.call_args.args[0]
        assert command[-len(expected) - 2 : -2] == expected
        assert command[-2] == "/Out"
        assert subprocess_mock.call_args.kwargs["timeout"] == 600


@pytest.mark.parametrize("flags", [[], ["--force"], ["--yes"]])
def test_cli_non_tty_never_restores_without_force_yes(
    ns, ctx, subprocess_mock, mocker, stdin, caplog, flags
):
    mocker.patch("scripts.onec_ops.check_environment")
    stdin.isatty.return_value = False
    assert main([
        "--platform", str(ctx.platform_path), "--ib", str(ns.ib),
        "restore-dt", "--from", str(ns.from_), *flags,
    ]) == 1
    assert "--force --yes" in caplog.text
    subprocess_mock.assert_not_called()
    stdin.readline.assert_not_called()


def test_cli_cancellation_never_starts_restore(ns, ctx, subprocess_mock, mocker, stdin):
    mocker.patch("scripts.onec_ops.check_environment")
    stdin.readline.return_value = "n\n"
    assert main([
        "--platform", str(ctx.platform_path), "--ib", str(ns.ib),
        "restore-dt", "--from", str(ns.from_), "--force",
    ]) == 1
    subprocess_mock.assert_not_called()
    assert (ns.ib / "1Cv8.1CD").read_bytes() == b"existing database"
