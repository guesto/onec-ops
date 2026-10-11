"""Тесты действия load-epf."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import pytest

from scripts.actions.load_epf import LoadEpfAction
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
    source = tmp_path / "Обработка.xml"
    source.write_bytes(b"<MetaDataObject/>")
    return argparse.Namespace(ib=ib, root=source, epf=tmp_path / "nested" / "test.epf")


@pytest.fixture
def ctx(tmp_path):
    platform = tmp_path / "1cv8"
    platform.touch()
    platform.chmod(0o755)
    return RunContext(platform)


def test_validate_missing_ib(ns):
    ns.ib = None
    with pytest.raises(OneCOpsError, match="--ib"):
        LoadEpfAction().validate(ns)


def test_validate_missing_root(ns):
    ns.root = None
    with pytest.raises(OneCOpsError, match="--root"):
        LoadEpfAction().validate(ns)


def test_validate_root_not_exists(ns):
    ns.root.unlink()
    with pytest.raises(OneCOpsError, match="не существует"):
        LoadEpfAction().validate(ns)


def test_validate_root_empty(ns):
    ns.root.write_bytes(b"")
    with pytest.raises(OneCOpsError, match="пустой"):
        LoadEpfAction().validate(ns)


def test_validate_root_wrong_suffix(ns):
    ns.root = ns.root.rename(ns.root.with_suffix(".txt"))
    with pytest.raises(OneCOpsError, match="должен иметь расширение"):
        LoadEpfAction().validate(ns)


def test_validate_source_is_directory(ns):
    ns.root.unlink()
    ns.root.mkdir()
    with pytest.raises(OneCOpsError, match="должен быть файлом"):
        LoadEpfAction().validate(ns)


@pytest.mark.parametrize("suffix", [".xml", ".XML"])
def test_validate_ok(ns, suffix):
    ns.root = ns.root.rename(ns.root.with_suffix(suffix))
    LoadEpfAction().validate(ns)


def test_validate_destination_is_directory(ns):
    ns.epf.mkdir(parents=True)
    with pytest.raises(OneCOpsError, match="должен указывать на файл"):
        LoadEpfAction().validate(ns)


def test_validate_output_not_writable(ns, mocker):
    mocker.patch("scripts.actions.load_epf.os.access", return_value=False)
    with pytest.raises(OneCOpsError, match="недоступен для записи"):
        LoadEpfAction().validate(ns)


def test_validate_parent_is_file(ns):
    ns.epf.parent.touch()
    with pytest.raises(OneCOpsError, match="каталогом"):
        LoadEpfAction().validate(ns)


def test_build_1c_args_order_and_absolute_paths(ns, ctx, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ns.ib = Path("ib")
    ns.root = Path("Обработка.xml")
    ns.epf = Path("nested/test.erf")
    action = LoadEpfAction()
    action.resolve_paths(ns)
    assert ns.ib == tmp_path / "ib"
    assert ns.root == tmp_path / "Обработка.xml"
    assert ns.epf == tmp_path / "nested/test.erf"
    assert action.build_1c_args(ns, ctx) == [
        "DESIGNER",
        "/F",
        str(tmp_path / "ib"),
        "/DisableStartupDialogs",
        "/LoadExternalDataProcessorOrReportFromFiles",
        str(tmp_path / "Обработка.xml"),
        str(tmp_path / "nested/test.erf"),
    ]


def test_pre_run_creates_parent_directory(ns, ctx):
    LoadEpfAction().pre_run(ns, ctx)
    assert ns.epf.parent.is_dir()
    assert not ns.epf.exists()


def test_pre_run_directory_error(ns, ctx, mocker):
    mocker.patch("scripts.actions.load_epf.Path.mkdir", side_effect=PermissionError("denied"))
    with pytest.raises(OneCOpsError, match="Не удалось"):
        LoadEpfAction().pre_run(ns, ctx)


@pytest.mark.parametrize("dry_run", [False, True])
def test_cli_runs_with_mocked_subprocess(ns, ctx, subprocess_mock, mocker, caplog, dry_run):
    mocker.patch("scripts.onec_ops.check_environment")
    mocker.patch("scripts.lib.runner.shutil.which", return_value="/usr/bin/xvfb-run")
    argv = [
        "--platform",
        str(ctx.platform_path),
        "--ib",
        str(ns.ib),
        "load-epf",
        "--root",
        str(ns.root),
        "--epf",
        str(ns.epf),
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
        expected = LoadEpfAction().build_1c_args(ns, ctx)
        assert subprocess_mock.call_args.args[0][-len(expected) :] == expected
        assert subprocess_mock.call_args.kwargs["timeout"] == 600
