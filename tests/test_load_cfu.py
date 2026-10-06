"""Тесты действия load-cfu."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import pytest

from scripts.actions.load_cfu import LoadCfuAction
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
        from_=tmp_path / "nested" / "config.cfu",
        extension="TestExt",
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


def test_validate_requires_extension(ns):
    ns.extension = None
    with pytest.raises(OneCOpsError, match="--extension"):
        LoadCfuAction().validate(ns)


def test_validate_missing_from(ns):
    ns.from_ = None
    with pytest.raises(OneCOpsError, match="--from"):
        LoadCfuAction().validate(ns)


def test_validate_file_not_exists(ns):
    with pytest.raises(OneCOpsError, match="не существует"):
        LoadCfuAction().validate(ns)


def test_validate_file_empty(ns):
    ns.from_.parent.mkdir()
    ns.from_.touch()
    with pytest.raises(OneCOpsError, match="пустой"):
        LoadCfuAction().validate(ns)


def test_validate_source_is_directory(ns):
    ns.from_.mkdir(parents=True)
    with pytest.raises(OneCOpsError, match="файлом"):
        LoadCfuAction().validate(ns)


def test_validate_ok(ns):
    ns.from_.parent.mkdir()
    ns.from_.write_bytes(b"configuration")
    LoadCfuAction().validate(ns)


def test_build_1c_args(ns, ctx, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ns.from_ = Path("nested/config.cfu")
    args = LoadCfuAction().build_1c_args(ns, ctx)
    assert args == [*_base_args(ns), "-Extension", "TestExt"]
    assert "/UpdateDBCfg" not in args


def test_build_1c_args_update_db_cfg(ns, ctx):
    ns.update_db_cfg = True
    assert LoadCfuAction().build_1c_args(ns, ctx) == [
        *_base_args(ns),
        "-Extension",
        "TestExt",
        "/UpdateDBCfg",
    ]


def test_cli_runs_with_mocked_subprocess(ns, ctx, mocker, subprocess_mock):
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
        "load-cfu",
        "--from",
        str(ns.from_),
    ]
    arguments += ["--extension", ns.extension]
    arguments += ["--update-db-cfg"]

    assert main(arguments) == 0

    subprocess_mock.assert_called_once()
    expected = LoadCfuAction().build_1c_args(ns, ctx)
    assert subprocess_mock.call_args.args[0][-len(expected) :] == expected
    assert subprocess_mock.call_args.kwargs["timeout"] == 600
