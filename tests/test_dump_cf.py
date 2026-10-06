"""Тесты действия dump-cf."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import pytest

from scripts.actions.dump_cf import DumpCfAction
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
        to=tmp_path / "nested" / "config.cf",
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
        "/DumpCfg",
        str(Path(ns.to).resolve()),
    ]


def test_validate_ok(ns):
    DumpCfAction().validate(ns)


def test_build_1c_args(ns, ctx, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ns.to = Path("nested/config.cf")
    args = DumpCfAction().build_1c_args(ns, ctx)
    assert args == _base_args(ns)


def test_pre_run_creates_parent_directory(ns, ctx):
    DumpCfAction().pre_run(ns, ctx)
    assert ns.to.parent.is_dir()
    assert not ns.to.exists()


def test_validate_warns_about_overwrite(ns, caplog):
    ns.to.parent.mkdir()
    ns.to.write_bytes(b"original")
    with caplog.at_level("WARNING"):
        DumpCfAction().validate(ns)
    assert "перезаписан" in caplog.text
    assert ns.to.read_bytes() == b"original"


def test_cli_runs_with_mocked_subprocess(ns, ctx, mocker, subprocess_mock):
    ctx.platform_path.touch()
    ctx.platform_path.chmod(0o755)
    mocker.patch("scripts.onec_ops.check_environment")
    mocker.patch("scripts.lib.runner.shutil.which", return_value="/usr/bin/xvfb-run")
    arguments = [
        "--platform",
        str(ctx.platform_path),
        "--ib",
        str(ns.ib),
        "dump-cf",
        "--to",
        str(ns.to),
    ]

    assert main(arguments) == 0

    subprocess_mock.assert_called_once()
    expected = DumpCfAction().build_1c_args(ns, ctx)
    assert subprocess_mock.call_args.args[0][-len(expected) :] == expected
    assert subprocess_mock.call_args.kwargs["timeout"] == 600
