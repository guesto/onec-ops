"""Тесты выгрузки базы в .dt."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import pytest

from scripts.actions.dump_dt import DumpDtAction
from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext
from scripts.onec_ops import build_parser, main


@pytest.fixture(autouse=True)
def subprocess_mock(mocker):
    mocker.patch("subprocess.Popen")
    return mocker.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, "", ""))


@pytest.fixture
def ns(tmp_path):
    ib = tmp_path / "ib"
    ib.mkdir()
    (ib / "1Cv8.1CD").touch()
    return argparse.Namespace(ib=ib, to=tmp_path / "nested" / "backups" / "base.dt")


@pytest.fixture
def ctx(tmp_path):
    platform = tmp_path / "1cv8"
    platform.touch()
    platform.chmod(0o755)
    return RunContext(platform)


def test_validate_missing_ib(ns):
    ns.ib = None
    with pytest.raises(OneCOpsError, match="--ib"):
        DumpDtAction().validate(ns)


def test_validate_ib_without_database(ns):
    (ns.ib / "1Cv8.1CD").unlink()
    with pytest.raises(OneCOpsError, match="1Cv8.1CD"):
        DumpDtAction().validate(ns)


def test_validate_missing_to(ns):
    ns.to = None
    with pytest.raises(OneCOpsError, match="--to"):
        DumpDtAction().validate(ns)


def test_parser_requires_to(ns):
    with pytest.raises(SystemExit) as error:
        build_parser().parse_args(["dump-dt", "--ib", str(ns.ib)])
    assert error.value.code == 2


def test_validate_other_suffix_warns(ns, caplog):
    ns.to = ns.to.with_suffix(".bin")
    with caplog.at_level("WARNING"):
        DumpDtAction().validate(ns)
    assert "ожидается .dt" in caplog.text
    assert str(ns.to) in caplog.text


@pytest.mark.parametrize("suffix", [".dt", ".DT"])
def test_validate_ok(ns, suffix, caplog):
    ns.to = ns.to.with_suffix(suffix)
    DumpDtAction().validate(ns)
    assert not caplog.records
    assert not ns.to.parent.exists()


def test_validate_destination_is_directory(ns):
    ns.to.mkdir(parents=True)
    with pytest.raises(OneCOpsError, match="должен указывать на файл"):
        DumpDtAction().validate(ns)


def test_validate_parent_is_file(ns):
    ns.to.parent.parent.touch()
    with pytest.raises(OneCOpsError, match="каталогом"):
        DumpDtAction().validate(ns)


def test_validate_parent_not_writable(ns, mocker):
    mocker.patch("scripts.actions.dump_dt.os.access", return_value=False)
    with pytest.raises(OneCOpsError, match="недоступен для записи"):
        DumpDtAction().validate(ns)


def test_build_1c_args_with_absolute_paths(ns, ctx, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ns.ib = Path("ib")
    ns.to = Path("nested/backups/base.dt")
    action = DumpDtAction()
    action.resolve_paths(ns)
    assert ns.ib == tmp_path / "ib"
    assert ns.to == tmp_path / "nested/backups/base.dt"
    assert action.build_1c_args(ns, ctx) == [
        "DESIGNER",
        "/F",
        str(tmp_path / "ib"),
        "/DisableStartupDialogs",
        "/DumpIB",
        str(tmp_path / "nested/backups/base.dt"),
    ]


def test_pre_run_creates_parent_directory(ns, ctx):
    DumpDtAction().pre_run(ns, ctx)
    assert ns.to.parent.is_dir()
    assert not ns.to.exists()


def test_pre_run_warns_about_overwrite(ns, ctx, caplog):
    ns.to.parent.mkdir(parents=True)
    ns.to.write_bytes(b"original backup")
    with caplog.at_level("WARNING"):
        DumpDtAction().pre_run(ns, ctx)
    assert "перезаписан" in caplog.text
    assert str(ns.to) in caplog.text
    assert ns.to.read_bytes() == b"original backup"


def test_pre_run_directory_error(ns, ctx, mocker):
    mocker.patch("scripts.actions.dump_dt.Path.mkdir", side_effect=PermissionError("denied"))
    with pytest.raises(OneCOpsError, match="Не удалось создать каталог"):
        DumpDtAction().pre_run(ns, ctx)


@pytest.mark.parametrize("dry_run", [False, True])
def test_cli_runs_with_mocked_subprocess(ns, ctx, subprocess_mock, mocker, caplog, dry_run):
    mocker.patch("scripts.onec_ops.check_environment")
    mocker.patch("scripts.lib.runner.shutil.which", return_value="/usr/bin/xvfb-run")
    argv = [
        "--platform", str(ctx.platform_path), "--ib", str(ns.ib),
        "dump-dt", "--to", str(ns.to),
    ]
    if dry_run:
        argv += ["--dry-run"]
    with caplog.at_level("INFO"):
        assert main(argv) == 0
    assert ns.to.parent.is_dir()
    assert not ns.to.exists()
    if dry_run:
        subprocess_mock.assert_not_called()
        assert "Dry-run" in caplog.text
        assert "/DumpIB" in caplog.text
    else:
        subprocess_mock.assert_called_once()
        expected = DumpDtAction().build_1c_args(ns, ctx)
        command = subprocess_mock.call_args.args[0]
        assert command[-len(expected) - 2 : -2] == expected
        assert command[-2] == "/Out"
        assert subprocess_mock.call_args.kwargs["timeout"] == 600
