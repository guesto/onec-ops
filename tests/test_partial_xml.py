"""Тесты частичной выгрузки и загрузки XML."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pytest

from scripts.onec_ops import main

MODULE = "Catalogs/Клиенты/Ext/ObjectModule.bsl"


@pytest.fixture
def ib(tmp_path):
    path = tmp_path / "ib"
    path.mkdir()
    (path / "1Cv8.1CD").touch()
    return path


@pytest.fixture
def source(tmp_path):
    """Каталог частичной загрузки без Configuration.xml."""
    root = tmp_path / "xml"
    module = root / MODULE
    module.parent.mkdir(parents=True)
    module.write_text("Процедура А() КонецПроцедуры", encoding="utf-8")
    return root


@pytest.fixture
def captured(mocker):
    """Запоминает команду 1С и содержимое списка на момент запуска."""
    state = {"command": None, "list": None, "list_path": None, "returncode": 0, "exception": None}

    def run(command, **kwargs):
        state["command"] = command
        if "-listFile" in command:
            path = Path(command[command.index("-listFile") + 1])
            state["list_path"] = path
            state["list"] = path.read_text(encoding="utf-8-sig").splitlines()
        if state["exception"]:
            raise state["exception"]
        return subprocess.CompletedProcess(command, state["returncode"], "", "")

    mocker.patch("scripts.lib.runner._execute", side_effect=run)
    return state


@pytest.fixture
def cli(tmp_path, ib, mocker):
    platform = tmp_path / "1cv8"
    platform.touch()
    platform.chmod(0o755)
    mocker.patch("scripts.onec_ops.check_environment")
    mocker.patch("scripts.lib.runner.shutil.which", return_value="/usr/bin/xvfb-run")

    def run(*argv):
        return main(["--platform", str(platform), "--ib", str(ib), *argv])

    return run


def _write_list(tmp_path, content: bytes) -> Path:
    path = tmp_path / "список с пробелом.txt"
    path.write_bytes(content)
    return path


def test_dump_objects(cli, captured, tmp_path):
    code = cli(
        "dump-config",
        "--to",
        str(tmp_path / "out"),
        "--object",
        "Catalog.А",
        "--object",
        "Document.Б",
    )

    assert code == 0
    assert captured["list"] == ["Catalog.А", "Document.Б"]
    assert "-listFile" in captured["command"]
    assert not captured["list_path"].exists()


def test_dump_list_file_with_bom_crlf_and_blank_lines_keeps_user_file(cli, captured, tmp_path):
    content = "﻿Catalog.А\r\n\r\nDocument.Б\r\n".encode()
    list_file = _write_list(tmp_path, content)

    assert cli("dump-config", "--to", str(tmp_path / "out"), "--list-file", str(list_file)) == 0
    assert captured["list"] == ["Catalog.А", "Document.Б"]
    assert list_file.read_bytes() == content
    assert captured["list_path"] != list_file


def test_dump_with_extension(cli, captured, tmp_path):
    code = cli(
        "dump-config", "--to", str(tmp_path / "out"), "--object", "Catalog.А", "--extension", "Р"
    )

    assert code == 0
    index = captured["command"].index("-Extension")
    assert captured["command"][index + 1] == "Р"
    assert captured["command"][index - 2] == "-listFile"


def test_full_dump_has_no_list(cli, captured, tmp_path):
    assert cli("dump-config", "--to", str(tmp_path / "out")) == 0
    assert "-listFile" not in captured["command"]


@pytest.mark.parametrize(
    ("action", "option", "value"),
    [("dump-config", "--object", "Catalog.А"), ("load-config", "--file", MODULE)],
)
class TestRejectedBeforeStart:
    @staticmethod
    def _target(action, tmp_path, source):
        return (
            ["--to", str(tmp_path / "out")] if action == "dump-config" else ["--from", str(source)]
        )

    def test_blank_value(self, action, option, value, cli, captured, tmp_path, source):
        assert cli(action, *self._target(action, tmp_path, source), option, " ") == 1
        assert captured["command"] is None

    def test_with_list_file(self, action, option, value, cli, captured, tmp_path, source):
        list_file = _write_list(tmp_path, value.encode())
        argv = [option, value, "--list-file", str(list_file)]

        assert cli(action, *self._target(action, tmp_path, source), *argv) == 1
        assert captured["command"] is None

    def test_with_all_extensions(
        self, action, option, value, cli, captured, tmp_path, source, caplog
    ):
        assert (
            cli(action, *self._target(action, tmp_path, source), option, value, "--all-extensions")
            == 1
        )
        assert captured["command"] is None
        assert "--all-extensions" in caplog.text

    @pytest.mark.parametrize(
        "content", [b"", b"  \r\n\r\n", b"\xef\xbb\xbf"], ids=["empty", "blank", "bom"]
    )
    def test_empty_list_file(
        self, action, option, value, content, cli, captured, tmp_path, source, caplog
    ):
        list_file = _write_list(tmp_path, content)

        assert (
            cli(action, *self._target(action, tmp_path, source), "--list-file", str(list_file)) == 1
        )
        assert captured["command"] is None
        assert "пуст" in caplog.text

    def test_missing_list_file(
        self, action, option, value, cli, captured, tmp_path, source, caplog
    ):
        missing = tmp_path / "нет.txt"

        assert (
            cli(action, *self._target(action, tmp_path, source), "--list-file", str(missing)) == 1
        )
        assert captured["command"] is None
        assert "Traceback" not in caplog.text

    def test_wrong_encoding(self, action, option, value, cli, captured, tmp_path, source, caplog):
        list_file = _write_list(tmp_path, "Каталог".encode("cp1251"))

        assert (
            cli(action, *self._target(action, tmp_path, source), "--list-file", str(list_file)) == 1
        )
        assert captured["command"] is None
        assert "UTF-8" in caplog.text


def test_load_file_without_configuration_xml_and_dump_info(cli, captured, source):
    assert cli("load-config", "--from", str(source), "--file", MODULE) == 0
    assert captured["list"] == [str(Path(MODULE))]
    assert "-updateConfigDumpInfo" not in captured["command"]
    assert not captured["list_path"].exists()


def test_load_list_file_with_absolute_path_and_update_db(cli, captured, tmp_path, source):
    list_file = _write_list(tmp_path, f"{source / MODULE}\n".encode())

    assert (
        cli("load-config", "--from", str(source), "--list-file", str(list_file), "--update-db-cfg")
        == 0
    )
    assert captured["list"] == [str(Path(MODULE))]
    assert captured["command"][captured["command"].index("/UpdateDBCfg") - 2] == "-listFile"


def test_load_with_extension(cli, captured, source):
    assert cli("load-config", "--from", str(source), "--file", MODULE, "--extension", "Р") == 0
    assert captured["command"][-4:-2] == ["-Extension", "Р"]


def test_full_load_still_requires_configuration_xml(cli, captured, source, caplog):
    assert cli("load-config", "--from", str(source)) == 1
    assert "Configuration.xml" in caplog.text
    assert captured["command"] is None


def test_full_load_keeps_dump_info(cli, captured, source):
    (source / "Configuration.xml").touch()

    assert cli("load-config", "--from", str(source)) == 0
    assert "-updateConfigDumpInfo" in captured["command"]
    assert "-listFile" not in captured["command"]


@pytest.mark.parametrize(
    ("item", "message"),
    [("../вне.xml", "вне каталога"), ("Нет/Такого.xml", "не найден"), ("Catalogs", "не найден")],
)
def test_load_rejects_bad_paths(cli, captured, source, tmp_path, caplog, item, message):
    (tmp_path / "вне.xml").touch()

    assert cli("load-config", "--from", str(source), "--file", item) == 1
    assert captured["command"] is None
    assert message in caplog.text


@pytest.mark.parametrize("failure", ["returncode", "timeout"])
def test_temp_list_removed_on_failure(cli, captured, source, failure):
    if failure == "returncode":
        captured["returncode"] = 1
    else:
        captured["exception"] = subprocess.TimeoutExpired("1cv8", 1)

    assert cli("load-config", "--from", str(source), "--file", MODULE) == 1
    assert captured["list_path"] is not None
    assert not captured["list_path"].exists()


def test_temp_list_removed_on_dry_run(cli, source, mocker):
    created = []
    real = tempfile.mkstemp

    def spy(*args, **kwargs):
        fd, name = real(*args, **kwargs)
        created.append(Path(name))
        return fd, name

    mocker.patch("scripts.actions.partial_list.tempfile.mkstemp", side_effect=spy)
    run = mocker.patch("scripts.lib.runner._execute")

    assert cli("--dry-run", "load-config", "--from", str(source), "--file", MODULE) == 0
    run.assert_not_called()
    assert len(created) == 1
    assert not created[0].exists()
