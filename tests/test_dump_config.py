"""Тесты действия dump-config."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from scripts.actions.dump_config import DumpConfigAction
from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext


def _namespace(tmp_path: Path, **options) -> argparse.Namespace:
    ib = tmp_path / "ib"
    ib.mkdir(exist_ok=True)
    (ib / "1Cv8.1CD").touch()
    values = {
        "ib": ib,
        "to": tmp_path / "xml",
        "format": None,
        "extension": None,
        "all_extensions": False,
    }
    values.update(options)
    return argparse.Namespace(**values)


def _base_args(ns: argparse.Namespace) -> list[str]:
    return [
        "DESIGNER",
        "/F",
        str(ns.ib),
        "/DisableStartupDialogs",
        "/DumpConfigToFiles",
        str(Path(ns.to).resolve()),
    ]


def test_validate_extension_and_all_extensions_mutually_exclusive(tmp_path):
    with pytest.raises(OneCOpsError, match="взаимоисключающие"):
        DumpConfigAction().validate(_namespace(tmp_path, extension="Test", all_extensions=True))


def test_validate_ok(tmp_path):
    DumpConfigAction().validate(_namespace(tmp_path))


def test_build_1c_args_default_no_format(tmp_path):
    parser = argparse.ArgumentParser()
    action = DumpConfigAction()
    action.add_arguments(parser)
    ns = parser.parse_args(["--to", str(tmp_path / "xml")])
    ns.ib = tmp_path / "ib"

    args = action.build_1c_args(ns, RunContext(tmp_path / "1cv8"))

    assert ns.format is None
    assert args == _base_args(ns)
    assert "-Format" not in args


def test_build_1c_args_format_none(tmp_path):
    ns = _namespace(tmp_path, format=None)
    args = DumpConfigAction().build_1c_args(ns, RunContext(tmp_path / "1cv8"))
    assert args == _base_args(ns)
    assert "-Format" not in args


def test_build_1c_args_plain_format(tmp_path):
    ns = _namespace(tmp_path, format="plain")
    args = DumpConfigAction().build_1c_args(ns, RunContext(tmp_path / "1cv8"))
    assert args == [*_base_args(ns), "-Format", "plain"]


def test_build_1c_args_extension(tmp_path):
    ns = _namespace(tmp_path, extension="Test")
    assert DumpConfigAction().build_1c_args(ns, RunContext(tmp_path / "1cv8")) == [
        *_base_args(ns),
        "-Extension",
        "Test",
    ]


def test_build_1c_args_all_extensions(tmp_path):
    ns = _namespace(tmp_path, all_extensions=True)
    assert DumpConfigAction().build_1c_args(ns, RunContext(tmp_path / "1cv8")) == [
        *_base_args(ns),
        "-AllExtensions",
    ]


def test_pre_run_creates_directory(tmp_path):
    ns = _namespace(tmp_path, to=tmp_path / "nested" / "xml")
    DumpConfigAction().pre_run(ns, RunContext(tmp_path / "1cv8"))
    assert ns.to.is_dir()


def test_pre_run_warns_about_overwrite(tmp_path, caplog):
    ns = _namespace(tmp_path)
    ns.to.mkdir()
    old_file = ns.to / "Configuration.xml"
    old_file.write_text("original", encoding="utf-8")
    with caplog.at_level("WARNING"):
        DumpConfigAction().pre_run(ns, RunContext(tmp_path / "1cv8"))
    assert "перезаписаны" in caplog.text
    assert old_file.read_text(encoding="utf-8") == "original"


def test_validate_missing_to(tmp_path):
    with pytest.raises(OneCOpsError, match="--to"):
        DumpConfigAction().validate(_namespace(tmp_path, to=None))


def test_validate_destination_is_file(tmp_path):
    path = tmp_path / "file"
    path.touch()
    with pytest.raises(OneCOpsError, match="каталогом"):
        DumpConfigAction().validate(_namespace(tmp_path, to=path / "xml"))


def test_validate_destination_not_writable(tmp_path, mocker):
    mocker.patch("scripts.actions.dump_config.os.access", return_value=False)
    with pytest.raises(OneCOpsError, match="недоступен для записи"):
        DumpConfigAction().validate(_namespace(tmp_path))


def test_pre_run_directory_error(tmp_path, mocker):
    ns = _namespace(tmp_path)
    mocker.patch("scripts.actions.dump_config.Path.mkdir", side_effect=PermissionError("denied"))
    with pytest.raises(OneCOpsError, match="Не удалось подготовить"):
        DumpConfigAction().pre_run(ns, RunContext(tmp_path / "1cv8"))
