"""Тесты действия load-cf."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import pytest

from scripts.actions.load_cf import LoadCfAction
from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext
from scripts.onec_ops import main


@pytest.fixture(autouse=True)
def subprocess_mock(mocker):
    return mocker.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, "", ""))


@pytest.fixture
def ns(tmp_path):
    ib = tmp_path / "ib"
    ib.mkdir()
    (ib / "1Cv8.1CD").touch()
    return argparse.Namespace(
        ib=ib,
        from_=tmp_path / "nested" / "config.cf",
        extension=None,
        update_db_cfg=False,
    )


@pytest.fixture
def ctx(tmp_path):
    return RunContext(tmp_path / "1cv8")


def _base_args(ns):
    return [
        "DESIGNER",
        "/F",
        str(ns.ib),
        "/DisableStartupDialogs",
        "/LoadCfg",
        str(Path(ns.from_).resolve()),
    ]


def test_validate_missing_from(ns):
    ns.from_ = None
    with pytest.raises(OneCOpsError, match="--from"):
        LoadCfAction().validate(ns)


def test_validate_file_not_exists(ns):
    with pytest.raises(OneCOpsError, match="не существует"):
        LoadCfAction().validate(ns)


def test_validate_file_empty(ns):
    ns.from_.parent.mkdir()
    ns.from_.touch()
    with pytest.raises(OneCOpsError, match="пустой"):
        LoadCfAction().validate(ns)


def test_validate_source_is_directory(ns):
    ns.from_.mkdir(parents=True)
    with pytest.raises(OneCOpsError, match="файлом"):
        LoadCfAction().validate(ns)


def test_validate_ok(ns):
    ns.from_.parent.mkdir()
    ns.from_.write_bytes(b"configuration")
    LoadCfAction().validate(ns)


def test_build_1c_args(ns, ctx, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ns.from_ = Path("nested/config.cf")
    args = LoadCfAction().build_1c_args(ns, ctx)
    assert args == _base_args(ns)
    assert "/UpdateDBCfg" not in args


def test_build_1c_args_update_db_cfg(ns, ctx):
    ns.update_db_cfg = True
    assert LoadCfAction().build_1c_args(ns, ctx) == [
        *_base_args(ns),
        "/UpdateDBCfg",
    ]


@pytest.mark.parametrize("extension", [None, "TestExt"])
def test_cli_runs_with_mocked_subprocess(ns, ctx, mocker, subprocess_mock, extension):
    ns.extension = extension
    if extension:
        ns.from_ = ns.from_.with_suffix(".cfe")
    ctx.platform_path.touch()
    ctx.platform_path.chmod(0o755)
    mocker.patch("scripts.onec_ops.check_environment")
    mocker.patch("scripts.lib.runner.shutil.which", return_value="/usr/bin/xvfb-run")
    ns.from_.parent.mkdir()
    ns.from_.write_bytes(b"configuration")
    ns.update_db_cfg = True
    arguments = [
        "--platform",
        str(ctx.platform_path),
        "--ib",
        str(ns.ib),
        "load-cf",
        "--from",
        str(ns.from_),
    ]
    arguments += ["--update-db-cfg"]

    if extension:
        arguments += ["--extension", extension]

    assert main(arguments) == 0

    subprocess_mock.assert_called_once()
    expected = LoadCfAction().build_1c_args(ns, ctx)
    assert subprocess_mock.call_args.args[0][-len(expected) :] == expected
    assert subprocess_mock.call_args.kwargs["timeout"] == 600


@pytest.mark.parametrize("suffix", [".cfe", ".CFE"])
def test_validate_cfe_requires_extension(ns, suffix):
    ns.from_ = ns.from_.with_suffix(suffix)
    ns.from_.parent.mkdir()
    ns.from_.write_bytes(b"configuration")
    with pytest.raises(OneCOpsError, match="требуется --extension"):
        LoadCfAction().validate(ns)


@pytest.mark.parametrize("suffix", [".cf", ".CF"])
def test_validate_cf_forbids_extension(ns, suffix):
    ns.from_ = ns.from_.with_suffix(suffix)
    ns.extension = "TestExt"
    ns.from_.parent.mkdir()
    ns.from_.write_bytes(b"configuration")
    with pytest.raises(OneCOpsError, match="--extension запрещён для .cf"):
        LoadCfAction().validate(ns)


@pytest.mark.parametrize("extension", [None, "TestExt"])
def test_validate_other_extension_warns(ns, caplog, extension):
    ns.from_ = ns.from_.with_suffix(".bin")
    ns.extension = extension
    ns.from_.parent.mkdir()
    ns.from_.write_bytes(b"configuration")
    with caplog.at_level("WARNING"):
        LoadCfAction().validate(ns)
    assert "Неизвестное расширение файла" in caplog.text
    assert str(ns.from_) in caplog.text


def test_validate_cfe_with_extension_ok(ns):
    ns.from_ = ns.from_.with_suffix(".cfe")
    ns.extension = "TestExt"
    ns.from_.parent.mkdir()
    ns.from_.write_bytes(b"configuration")
    LoadCfAction().validate(ns)


def test_build_1c_args_without_extension(ns, ctx):
    parser = argparse.ArgumentParser()
    action = LoadCfAction()
    action.add_arguments(parser)
    parsed = parser.parse_args(["--from", str(ns.from_)])
    parsed.ib = ns.ib
    args = action.build_1c_args(parsed, ctx)
    assert parsed.extension is None
    assert args == _base_args(ns)
    assert "-Extension" not in args


@pytest.mark.parametrize("update_db_cfg", [False, True])
def test_build_1c_args_with_extension(ns, ctx, update_db_cfg):
    ns.update_db_cfg = update_db_cfg
    ns.from_ = ns.from_.with_suffix(".cfe")
    ns.extension = "TestExt"
    expected = [*_base_args(ns), "-Extension", "TestExt"]
    if update_db_cfg:
        expected += ["/UpdateDBCfg"]
    assert LoadCfAction().build_1c_args(ns, ctx) == expected
