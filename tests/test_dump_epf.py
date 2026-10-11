"""Тесты действия dump-epf."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import pytest

from scripts.actions.dump_epf import DumpEpfAction
from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext
from scripts.onec_ops import main


@pytest.fixture(autouse=True)
def subprocess_mock(mocker):
    mocker.patch("subprocess.Popen")
    return mocker.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, "", ""))


@pytest.fixture
def ns(tmp_path):
    ib = tmp_path / "ib"
    ib.mkdir()
    (ib / "1Cv8.1CD").touch()
    source = tmp_path / "Обработка.epf"
    source.write_bytes(b"external processing")
    return argparse.Namespace(ib=ib, epf=source, to=tmp_path / "nested" / "xml")


@pytest.fixture
def ctx(tmp_path):
    platform = tmp_path / "1cv8"
    platform.touch()
    platform.chmod(0o755)
    return RunContext(platform)


def test_validate_missing_ib(ns):
    ns.ib = None
    with pytest.raises(OneCOpsError, match="--ib"):
        DumpEpfAction().validate(ns)


def test_validate_missing_epf(ns):
    ns.epf = None
    with pytest.raises(OneCOpsError, match="--epf"):
        DumpEpfAction().validate(ns)


def test_validate_epf_not_exists(ns):
    ns.epf.unlink()
    with pytest.raises(OneCOpsError, match="не существует"):
        DumpEpfAction().validate(ns)


def test_validate_epf_empty(ns):
    ns.epf.write_bytes(b"")
    with pytest.raises(OneCOpsError, match="пустой"):
        DumpEpfAction().validate(ns)


def test_validate_epf_wrong_suffix(ns):
    ns.epf = ns.epf.rename(ns.epf.with_suffix(".txt"))
    with pytest.raises(OneCOpsError, match="должен иметь расширение"):
        DumpEpfAction().validate(ns)


def test_validate_source_is_directory(ns):
    ns.epf.unlink()
    ns.epf.mkdir()
    with pytest.raises(OneCOpsError, match="должен быть файлом"):
        DumpEpfAction().validate(ns)


@pytest.mark.parametrize("suffix", [".epf", ".EPF"])
def test_validate_ok_epf(ns, suffix):
    ns.epf = ns.epf.rename(ns.epf.with_suffix(suffix))
    DumpEpfAction().validate(ns)


@pytest.mark.parametrize("suffix", [".erf", ".ERF"])
def test_validate_ok_erf(ns, suffix):
    ns.epf = ns.epf.rename(ns.epf.with_suffix(suffix))
    DumpEpfAction().validate(ns)


def test_validate_destination_is_file(ns):
    ns.to.parent.mkdir()
    ns.to.touch()
    with pytest.raises(OneCOpsError, match="каталогом"):
        DumpEpfAction().validate(ns)


def test_validate_output_not_writable(ns, mocker):
    mocker.patch("scripts.actions.dump_epf.os.access", return_value=False)
    with pytest.raises(OneCOpsError, match="недоступен для записи"):
        DumpEpfAction().validate(ns)


def test_validate_parent_is_file(ns):
    ns.to.parent.touch()
    with pytest.raises(OneCOpsError, match="каталогом"):
        DumpEpfAction().validate(ns)


def test_build_1c_args_order_and_absolute_paths(ns, ctx, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ns.ib = Path("ib")
    ns.epf = Path("Обработка.epf")
    ns.to = Path("nested/xml")
    action = DumpEpfAction()
    action.resolve_paths(ns)
    assert ns.ib == tmp_path / "ib"
    assert ns.epf == tmp_path / "Обработка.epf"
    assert ns.to == tmp_path / "nested/xml"
    assert action.build_1c_args(ns, ctx) == [
        "DESIGNER",
        "/F",
        str(tmp_path / "ib"),
        "/DisableStartupDialogs",
        "/DumpExternalDataProcessorOrReportToFiles",
        str(tmp_path / "nested/xml"),
        str(tmp_path / "Обработка.epf"),
    ]


def test_pre_run_creates_directory(ns, ctx):
    DumpEpfAction().pre_run(ns, ctx)
    assert ns.to.is_dir()


def test_pre_run_warns_about_nonempty_directory(ns, ctx, caplog):
    ns.to.mkdir(parents=True)
    old = ns.to / "existing.xml"
    old.write_bytes(b"original")
    with caplog.at_level("WARNING"):
        DumpEpfAction().pre_run(ns, ctx)
    assert "непустой" in caplog.text
    assert old.read_bytes() == b"original"


def test_pre_run_directory_error(ns, ctx, mocker):
    mocker.patch("scripts.actions.dump_epf.Path.mkdir", side_effect=PermissionError("denied"))
    with pytest.raises(OneCOpsError, match="Не удалось"):
        DumpEpfAction().pre_run(ns, ctx)


@pytest.mark.parametrize("dry_run", [False, True])
def test_cli_runs_with_mocked_subprocess(ns, ctx, subprocess_mock, mocker, caplog, dry_run):
    mocker.patch("scripts.onec_ops.check_environment")
    mocker.patch("scripts.lib.runner.shutil.which", return_value="/usr/bin/xvfb-run")
    argv = [
        "--platform",
        str(ctx.platform_path),
        "--ib",
        str(ns.ib),
        "dump-epf",
        "--epf",
        str(ns.epf),
        "--to",
        str(ns.to),
    ]
    if dry_run:
        argv += ["--dry-run"]
    with caplog.at_level("INFO"):
        assert main(argv) == 0
    if dry_run:
        subprocess_mock.assert_not_called()
        assert "Dry-run" in caplog.text
    else:
        subprocess_mock.assert_called_once()
        expected = DumpEpfAction().build_1c_args(ns, ctx)
        assert subprocess_mock.call_args.args[0][-len(expected) :] == expected
        assert subprocess_mock.call_args.kwargs["timeout"] == 600
