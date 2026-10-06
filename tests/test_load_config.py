"""Тесты действия load-config."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from scripts.actions.load_config import LoadConfigAction
from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext


def _namespace(tmp_path: Path, **options) -> argparse.Namespace:
    ib = tmp_path / "ib"
    ib.mkdir(exist_ok=True)
    (ib / "1Cv8.1CD").touch()
    values = {
        "ib": ib,
        "from_": tmp_path / "xml",
        "extension": None,
        "all_extensions": False,
        "update_db_cfg": False,
    }
    values.update(options)
    return argparse.Namespace(**values)


def _base_args(ns: argparse.Namespace) -> list[str]:
    return [
        "DESIGNER",
        "/F",
        str(ns.ib),
        "/DisableStartupDialogs",
        "/LoadConfigFromFiles",
        str(Path(ns.from_).resolve()),
        "-updateConfigDumpInfo",
    ]


def test_validate_from_not_exists(tmp_path):
    with pytest.raises(OneCOpsError, match="не существует"):
        LoadConfigAction().validate(_namespace(tmp_path))


def test_validate_missing_configuration_xml(tmp_path):
    ns = _namespace(tmp_path)
    ns.from_.mkdir()
    with pytest.raises(OneCOpsError, match="Configuration.xml"):
        LoadConfigAction().validate(ns)


def test_validate_ok(tmp_path):
    ns = _namespace(tmp_path)
    ns.from_.mkdir()
    (ns.from_ / "Configuration.xml").touch()
    LoadConfigAction().validate(ns)


def test_build_1c_args_base(tmp_path):
    ns = _namespace(tmp_path)
    assert LoadConfigAction().build_1c_args(ns, RunContext(tmp_path / "1cv8")) == _base_args(ns)


def test_build_1c_args_update_db_cfg(tmp_path):
    ns = _namespace(tmp_path, update_db_cfg=True)
    assert LoadConfigAction().build_1c_args(ns, RunContext(tmp_path / "1cv8")) == [
        *_base_args(ns),
        "/UpdateDBCfg",
    ]


def test_build_1c_args_extension(tmp_path):
    ns = _namespace(tmp_path, extension="Test")
    assert LoadConfigAction().build_1c_args(ns, RunContext(tmp_path / "1cv8")) == [
        *_base_args(ns),
        "-Extension",
        "Test",
    ]


def test_build_1c_args_all_extensions(tmp_path):
    ns = _namespace(tmp_path, all_extensions=True, update_db_cfg=True)
    assert LoadConfigAction().build_1c_args(ns, RunContext(tmp_path / "1cv8")) == [
        *_base_args(ns),
        "-AllExtensions",
        "/UpdateDBCfg",
    ]


def test_validate_extension_and_all_extensions_mutually_exclusive(tmp_path):
    with pytest.raises(OneCOpsError, match="взаимоисключающие"):
        LoadConfigAction().validate(_namespace(tmp_path, extension="Test", all_extensions=True))


def test_validate_extension_without_configuration_xml(tmp_path):
    ns = _namespace(tmp_path, extension="Test")
    ns.from_.mkdir()
    LoadConfigAction().validate(ns)


def test_validate_missing_from(tmp_path):
    with pytest.raises(OneCOpsError, match="--from"):
        LoadConfigAction().validate(_namespace(tmp_path, from_=None))


def test_validate_source_is_file(tmp_path):
    ns = _namespace(tmp_path)
    ns.from_.touch()
    with pytest.raises(OneCOpsError, match="каталогом"):
        LoadConfigAction().validate(ns)


def test_validate_configuration_xml_is_directory(tmp_path):
    ns = _namespace(tmp_path)
    (ns.from_ / "Configuration.xml").mkdir(parents=True)
    with pytest.raises(OneCOpsError, match="Configuration.xml"):
        LoadConfigAction().validate(ns)
