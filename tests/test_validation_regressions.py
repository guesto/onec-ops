"""Регрессии проверки аргументов и ошибок файловой системы."""

from pathlib import Path

import pytest

from scripts.lib.config import resolve_platform
from scripts.lib.exceptions import PlatformNotFound
from scripts.lib.runner import RunContext, build_command
from scripts.onec_ops import main


@pytest.mark.parametrize("extension", ["", " \t"])
@pytest.mark.parametrize("action", ["dump-config", "load-config", "dump-cf", "load-cf"])
def test_blank_extension_never_runs_main_configuration(tmp_path, mocker, caplog, action, extension):
    ib = tmp_path / "ib"
    ib.mkdir()
    (ib / "1Cv8.1CD").touch()
    xml = tmp_path / "xml"
    xml.mkdir()
    (xml / "Configuration.xml").write_text("<Configuration/>", encoding="utf-8")
    cf = tmp_path / "config.cf"
    cf.write_bytes(b"configuration")
    option = "--from" if action.startswith("load") else "--to"
    source = xml if action.endswith("config") else cf
    mocker.patch("scripts.onec_ops.check_environment")
    run = mocker.patch("scripts.onec_ops.run_1c")

    assert main([action, "--ib", str(ib), option, str(source),
                 "--extension", extension]) == 1

    assert "Имя расширения --extension не может быть пустым" in caplog.text
    run.assert_not_called()
    assert cf.read_bytes() == b"configuration"


@pytest.mark.parametrize("source", ["cli", "env", "config"])
def test_relative_platform_uses_current_directory(tmp_path, monkeypatch, source):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ONEC_OPS_PLATFORM", raising=False)
    cli, config = None, {}
    if source == "cli":
        cli = Path("./1cv8")
    elif source == "env":
        monkeypatch.setenv("ONEC_OPS_PLATFORM", "./1cv8")
    else:
        config["platform"] = "./1cv8"

    assert resolve_platform(cli, config) == tmp_path / "1cv8"


@pytest.mark.parametrize("system", ["linux", "win32"])
def test_platform_directory_is_rejected_before_building_command(tmp_path, monkeypatch, system):
    monkeypatch.setattr("scripts.lib.runner.sys.platform", system)
    with pytest.raises(PlatformNotFound):
        build_command(["DESIGNER"], RunContext(tmp_path, dry_run=True))


@pytest.mark.parametrize("invalid_path", ["directory", "parent-file"])
def test_log_file_error_is_reported_before_platform_start(tmp_path, mocker, caplog, invalid_path):
    if invalid_path == "directory":
        log_file = tmp_path
    else:
        parent = tmp_path / "file"
        parent.touch()
        log_file = parent / "log.txt"
    check = mocker.patch("scripts.onec_ops.check_environment")
    run = mocker.patch("scripts.onec_ops.run_1c")

    assert main(["--log-file", str(log_file), "create-ib", "--type", "file",
                 "--path", str(tmp_path / "ib")]) == 1

    assert "Не удалось открыть файл журнала" in caplog.text
    assert str(log_file) in caplog.text
    check.assert_not_called()
    run.assert_not_called()


@pytest.mark.parametrize("invalid_path", ["file", "parent-file"])
def test_create_ib_file_path_error_is_reported_without_starting_platform(
    tmp_path, mocker, caplog, invalid_path,
):
    parent = tmp_path / "file"
    parent.write_text("keep", encoding="utf-8")
    path = parent if invalid_path == "file" else parent / "ib"
    mocker.patch("scripts.onec_ops.check_environment")
    run = mocker.patch("scripts.onec_ops.run_1c")

    assert main(["create-ib", "--type", "file", "--path", str(path), "--dry-run"]) == 1

    assert str(path) in caplog.text
    assert parent.read_text(encoding="utf-8") == "keep"
    run.assert_not_called()


def test_create_ib_permission_error_is_reported(tmp_path, mocker, caplog):
    path = tmp_path / "ib"
    mocker.patch("scripts.onec_ops.check_environment")
    mocker.patch("scripts.actions.create_ib_file.Path.mkdir", side_effect=PermissionError("denied"))
    run = mocker.patch("scripts.onec_ops.run_1c")

    assert main(["create-ib", "--type", "file", "--path", str(path)]) == 1

    assert "Не удалось подготовить каталог ИБ" in caplog.text
    assert str(path) in caplog.text
    run.assert_not_called()


def test_create_ib_removal_error_is_reported(tmp_path, mocker, caplog):
    database = tmp_path / "1Cv8.1CD"
    database.write_bytes(b"keep")
    mocker.patch("scripts.onec_ops.check_environment")
    mocker.patch("scripts.actions.create_ib_file.shutil.rmtree", side_effect=PermissionError("denied"))
    run = mocker.patch("scripts.onec_ops.run_1c")

    assert main(["create-ib", "--type", "file", "--path", str(tmp_path),
                 "--force", "--yes"]) == 1

    assert "Не удалось подготовить каталог ИБ" in caplog.text
    assert str(tmp_path) in caplog.text
    assert database.read_bytes() == b"keep"
    run.assert_not_called()
