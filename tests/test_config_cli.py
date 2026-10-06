"""Проверки общего механизма ИБ и новых команд через CLI."""

from __future__ import annotations

import subprocess

import pytest

from scripts.actions.dump_config import DumpConfigAction
from scripts.actions.load_config import LoadConfigAction
from scripts.lib.exceptions import OneCOpsError
from scripts.onec_ops import build_parser, main


@pytest.fixture(autouse=True)
def subprocess_mock(mocker):
    """Запрещает реальные дочерние процессы во всех CLI-тестах."""
    return mocker.patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, "", ""))


@pytest.mark.parametrize(
    "action_name, option", [("dump-config", "--to"), ("load-config", "--from")]
)
@pytest.mark.parametrize("position", ["before", "after"])
def test_ib_accepted_before_and_after_action(tmp_path, action_name, option, position):
    arguments = [action_name, option, str(tmp_path / "xml")]
    ib_arguments = ["--ib", str(tmp_path / "ib")]
    argv = ib_arguments + arguments if position == "before" else arguments + ib_arguments
    assert build_parser().parse_args(argv).ib == tmp_path / "ib"


@pytest.mark.parametrize(
    "action_class, option", [(DumpConfigAction, "--to"), (LoadConfigAction, "--from")]
)
@pytest.mark.parametrize("ib_state", ["missing_argument", "missing_file", "directory"])
def test_validate_requires_file_ib(tmp_path, action_class, option, ib_state):
    arguments = [action_class.name, option, str(tmp_path / "xml")]
    if ib_state != "missing_argument":
        arguments += ["--ib", str(tmp_path)]
    if ib_state == "directory":
        (tmp_path / "1Cv8.1CD").mkdir()
    namespace = build_parser().parse_args(arguments)
    with pytest.raises(OneCOpsError, match="--ib|1Cv8.1CD"):
        action_class().validate(namespace)


@pytest.mark.parametrize(
    "action_name, option", [("dump-config", "--to"), ("load-config", "--from")]
)
def test_paths_resolved_from_relative_cli_arguments(tmp_path, monkeypatch, action_name, option):
    monkeypatch.chdir(tmp_path)
    ns = build_parser().parse_args(["--ib", "ib", action_name, option, "xml"])
    action = DumpConfigAction() if action_name == "dump-config" else LoadConfigAction()
    action.resolve_paths(ns)
    assert ns.ib == tmp_path / "ib"
    assert getattr(ns, action.path_args[0]) == tmp_path / "xml"


@pytest.mark.parametrize(
    "action_name, option", [("dump-config", "--to"), ("load-config", "--from")]
)
def test_xml_path_argument_required(action_name, option, capsys):
    with pytest.raises(SystemExit) as error:
        build_parser().parse_args([action_name])
    assert error.value.code == 2
    assert option in capsys.readouterr().err


def test_invalid_dump_format_rejected(tmp_path):
    with pytest.raises(SystemExit) as error:
        build_parser().parse_args(["dump-config", "--to", str(tmp_path), "--format", "invalid"])
    assert error.value.code == 2


@pytest.mark.parametrize(
    "action_name, option, flag",
    [
        ("dump-config", "--to", "/DumpConfigToFiles"),
        ("load-config", "--from", "/LoadConfigFromFiles"),
    ],
)
@pytest.mark.parametrize("dry_run", [False, True])
def test_cli_uses_runner_with_absolute_paths(
    tmp_path,
    monkeypatch,
    mocker,
    subprocess_mock,
    caplog,
    action_name,
    option,
    flag,
    dry_run,
):
    monkeypatch.chdir(tmp_path)
    platform = tmp_path / "1cv8"
    platform.touch()
    platform.chmod(0o755)
    ib = tmp_path / "ib"
    ib.mkdir()
    (ib / "1Cv8.1CD").touch()
    xml = tmp_path / "xml"
    if action_name == "load-config":
        xml.mkdir()
        (xml / "Configuration.xml").write_text("<Configuration/>", encoding="utf-8")
    mocker.patch("scripts.lib.runner.shutil.which", return_value="/usr/bin/xvfb-run")
    arguments = ["--platform", str(platform), "--ib", "ib", action_name, option, "xml"]
    if dry_run:
        arguments += ["--dry-run"]
    if action_name == "load-config":
        arguments += ["--update-db-cfg"]

    with caplog.at_level("INFO"):
        assert main(arguments) == 0

    platform_calls = [call for call in subprocess_mock.call_args_list if "DESIGNER" in call.args[0]]
    if dry_run:
        assert not platform_calls
        assert flag in caplog.text
        assert str(ib) in caplog.text
        assert str(xml) in caplog.text
        if action_name == "load-config":
            assert "/UpdateDBCfg" in caplog.text
    else:
        assert len(platform_calls) == 1
        command = platform_calls[0].args[0]
        assert command[command.index("/F") + 1] == str(ib)
        assert command[command.index(flag) + 1] == str(xml)
        assert platform_calls[0].kwargs["timeout"] == 600
        if action_name == "load-config":
            assert command[-1] == "/UpdateDBCfg"
    assert xml.is_dir()
