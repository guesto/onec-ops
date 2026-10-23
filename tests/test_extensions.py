"""Тесты list-extensions, check-extension и delete-extension."""

from __future__ import annotations

import io
import subprocess
from pathlib import Path

import pytest

from scripts.actions.check_extension import CheckExtensionAction
from scripts.actions.delete_extension import DeleteExtensionAction
from scripts.actions.list_extensions import ListExtensionsAction, parse_extension_names
from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext
from scripts.onec_ops import build_parser, main

TARGET_ACTIONS = [CheckExtensionAction(), DeleteExtensionAction()]


def _fake_run(returncode: int, out_text: str):
    """Имитирует 1С: пишет out_text в файл /Out (последний аргумент) в UTF-8 с BOM."""
    def run(command, **kwargs):
        Path(command[-1]).write_bytes(out_text.encode("utf-8-sig"))
        return subprocess.CompletedProcess(command, returncode, "", "")
    return run


@pytest.fixture
def ib(tmp_path):
    path = tmp_path / "ib"
    path.mkdir()
    (path / "1Cv8.1CD").touch()
    return path


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


def _ns(action, *argv, ib=None):
    ns = build_parser().parse_args([action.name, *argv])
    ns.ib = ib
    return ns


@pytest.fixture
def ctx(tmp_path):
    return RunContext(tmp_path / "1cv8")


# --- разбор /Out -----------------------------------------------------------


@pytest.mark.parametrize(
    ("out_text", "expected"),
    [
        ("", []),
        ("onec", ["onec"]),
        ("onec\r\nРасширение_2\r\n", ["onec", "Расширение_2"]),
        ("Соединение с хранилищем конфигурации не установлено\nonec", ["onec"]),
        ("onec: Не найден объект\n  ext1  \n2bad\n", ["ext1"]),
    ],
)
def test_parse_extension_names(out_text, expected):
    assert parse_extension_names(out_text) == expected


# --- list-extensions -------------------------------------------------------


def test_list_build_1c_args(ib, ctx):
    ns = _ns(ListExtensionsAction(), ib=ib)
    assert ListExtensionsAction().build_1c_args(ns, ctx) == [
        "DESIGNER", "/F", str(ib), "/DisableStartupDialogs", "/DumpDBCfgList", "-AllExtensions",
    ]


def test_list_cli_prints_names_to_stdout(cli, mocker, capsys):
    mocker.patch(
        "subprocess.run",
        side_effect=_fake_run(0, "Соединение с хранилищем конфигурации не установлено\r\nonec\r\next2\r\n"),
    )
    assert cli("list-extensions") == 0
    assert capsys.readouterr().out == "onec\next2\n"


def test_list_cli_no_extensions(cli, mocker, capsys, caplog):
    mocker.patch("subprocess.run", side_effect=_fake_run(0, ""))
    with caplog.at_level("INFO"):
        assert cli("list-extensions") == 0
    assert capsys.readouterr().out == ""
    assert "Расширений нет" in caplog.text


def test_list_cli_dry_run(cli, mocker, capsys):
    run = mocker.patch("subprocess.run")
    assert cli("--dry-run", "list-extensions") == 0
    run.assert_not_called()
    assert capsys.readouterr().out == ""


# --- выбор расширения (check / delete) --------------------------------------


@pytest.mark.parametrize("action", TARGET_ACTIONS, ids=lambda action: action.name)
@pytest.mark.parametrize(
    ("argv", "message"),
    [
        ([], "--extension NAME или --all-extensions"),
        (["--extension", "onec", "--all-extensions"], "взаимоисключающие"),
        (["--extension", " "], "не может быть пустым"),
    ],
)
def test_target_validation(action, argv, message, ib):
    ns = _ns(action, *argv, ib=ib)
    with pytest.raises(OneCOpsError, match=message):
        action.validate(ns)


@pytest.mark.parametrize("action", TARGET_ACTIONS, ids=lambda action: action.name)
@pytest.mark.parametrize("argv", [["--extension", "onec"], ["--all-extensions"]])
def test_target_validation_ok(action, argv, ib):
    action.validate(_ns(action, *argv, ib=ib))


@pytest.mark.parametrize(
    ("action", "key"),
    [(CheckExtensionAction(), "/CheckCanApplyConfigurationExtensions"), (DeleteExtensionAction(), "/DeleteCfg")],
    ids=["check-extension", "delete-extension"],
)
@pytest.mark.parametrize(
    ("argv", "tail"),
    [(["--extension", "onec"], ["-Extension", "onec"]), (["--all-extensions"], ["-AllExtensions"])],
)
def test_target_build_1c_args(action, key, argv, tail, ib, ctx):
    ns = _ns(action, *argv, ib=ib)
    assert action.build_1c_args(ns, ctx) == [
        "DESIGNER", "/F", str(ib), "/DisableStartupDialogs", key, *tail,
    ]


# --- check-extension -------------------------------------------------------


@pytest.mark.parametrize(
    ("argv", "message"),
    [(["--extension", "onec"], "Расширение можно применить: onec"), (["--all-extensions"], "Все расширения можно применить")],
)
def test_check_cli_ok(cli, mocker, caplog, argv, message):
    mocker.patch("subprocess.run", side_effect=_fake_run(0, ""))
    with caplog.at_level("INFO"):
        assert cli("check-extension", *argv) == 0
    assert message in caplog.text


def test_check_cli_failure_shows_1c_reasons(cli, mocker, caplog):
    reason = "onec: Не найден объект Справочник.Номенклатура"
    mocker.patch("subprocess.run", side_effect=_fake_run(1, reason))
    assert cli("check-extension", "--extension", "onec") == 1
    assert reason in caplog.text
    assert "можно применить" not in caplog.text


def test_check_cli_dry_run(cli, mocker, caplog):
    run = mocker.patch("subprocess.run")
    with caplog.at_level("INFO"):
        assert cli("--dry-run", "check-extension", "--all-extensions") == 0
    run.assert_not_called()
    assert "можно применить" not in caplog.text


# --- delete-extension ------------------------------------------------------


def test_delete_cli_with_yes(cli, mocker, caplog):
    run = mocker.patch("subprocess.run", side_effect=_fake_run(0, "Расширение удалено: onec"))
    with caplog.at_level("WARNING"):
        assert cli("delete-extension", "--extension", "onec", "--yes") == 0
    run.assert_called_once()
    assert "-Extension" in run.call_args.args[0]
    assert "Данные объектов расширения будут потеряны" in caplog.text


@pytest.mark.parametrize(("answer", "code"), [("Y\n", 0), ("yes\n", 0), ("n\n", 1), ("\n", 1)])
def test_delete_cli_interactive(cli, mocker, monkeypatch, caplog, answer, code):
    run = mocker.patch("subprocess.run", side_effect=_fake_run(0, ""))
    stdin = io.StringIO(answer)
    stdin.isatty = lambda: True
    monkeypatch.setattr("sys.stdin", stdin)
    assert cli("delete-extension", "--all-extensions") == code
    if code == 0:
        run.assert_called_once()
    else:
        run.assert_not_called()
        assert "Отменено пользователем" in caplog.text


def test_delete_cli_without_tty_requires_yes(cli, mocker, monkeypatch, caplog):
    run = mocker.patch("subprocess.run")
    stdin = io.StringIO("")
    stdin.isatty = lambda: False
    monkeypatch.setattr("sys.stdin", stdin)
    assert cli("delete-extension", "--extension", "onec") == 1
    run.assert_not_called()
    assert "--yes" in caplog.text


def test_delete_cli_dry_run_with_yes(cli, mocker):
    run = mocker.patch("subprocess.run")
    assert cli("--dry-run", "delete-extension", "--extension", "onec", "--yes") == 0
    run.assert_not_called()


def test_delete_cli_missing_extension(cli, mocker, caplog):
    message = "расширение конфигурации с указанным именем не найдено: nosuch"
    mocker.patch("subprocess.run", side_effect=_fake_run(1, message))
    assert cli("delete-extension", "--extension", "nosuch", "--yes") == 1
    assert message in caplog.text
