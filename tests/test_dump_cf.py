"""Тесты действия dump-cf."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import pytest

from scripts.actions.dump_cf import DumpCfAction
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


@pytest.mark.parametrize("extension", [None, "TestExt"])
def test_cli_runs_with_mocked_subprocess(ns, ctx, mocker, subprocess_mock, extension):
    ns.extension = extension
    if extension:
        ns.to = ns.to.with_suffix(".cfe")
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

    if extension:
        arguments += ["--extension", extension]

    assert main(arguments) == 0

    subprocess_mock.assert_called_once()
    expected = DumpCfAction().build_1c_args(ns, ctx)
    assert subprocess_mock.call_args.args[0][-len(expected) :] == expected
    assert subprocess_mock.call_args.kwargs["timeout"] == 600


@pytest.mark.parametrize("suffix", [".cfe", ".CFE"])
def test_validate_cfe_requires_extension(ns, suffix):
    ns.to = ns.to.with_suffix(suffix)
    with pytest.raises(OneCOpsError, match="требуется --extension"):
        DumpCfAction().validate(ns)


@pytest.mark.parametrize("suffix", [".cf", ".CF"])
def test_validate_cf_forbids_extension(ns, suffix):
    ns.to = ns.to.with_suffix(suffix)
    ns.extension = "TestExt"
    with pytest.raises(OneCOpsError, match="--extension запрещён для .cf"):
        DumpCfAction().validate(ns)


@pytest.mark.parametrize("extension", [None, "TestExt"])
def test_validate_other_extension_warns(ns, caplog, extension):
    ns.to = ns.to.with_suffix(".bin")
    ns.extension = extension
    with caplog.at_level("WARNING"):
        DumpCfAction().validate(ns)
    assert "Неизвестное расширение файла" in caplog.text
    assert str(ns.to) in caplog.text


def test_validate_cfe_with_extension_ok(ns):
    ns.to = ns.to.with_suffix(".cfe")
    ns.extension = "TestExt"
    DumpCfAction().validate(ns)


def test_build_1c_args_without_extension(ns, ctx):
    parser = argparse.ArgumentParser()
    action = DumpCfAction()
    action.add_arguments(parser)
    parsed = parser.parse_args(["--to", str(ns.to)])
    parsed.ib = ns.ib
    args = action.build_1c_args(parsed, ctx)
    assert parsed.extension is None
    assert args == _base_args(ns)
    assert "-Extension" not in args


def test_build_1c_args_with_extension(ns, ctx):
    ns.to = ns.to.with_suffix(".cfe")
    ns.extension = "TestExt"
    expected = [*_base_args(ns), "-Extension", "TestExt"]
    assert DumpCfAction().build_1c_args(ns, ctx) == expected
