"""Тесты update-db."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.actions.update_db import UpdateDbAction
from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext
from scripts.onec_ops import build_parser, main


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


def _ns(*argv, ib=None):
    ns = build_parser().parse_args(["update-db", *argv])
    ns.ib = ib
    return ns


@pytest.mark.parametrize(
    ("argv", "tail"),
    [
        ([], []),
        (["--extension", "onec"], ["-Extension", "onec"]),
        (["--all-extensions"], ["-AllExtensions"]),
        (["--dynamic"], ["-Dynamic+"]),
        (["--no-dynamic"], ["-Dynamic-"]),
        (["--warnings-as-errors"], ["-WarningsAsErrors"]),
        (
            ["--extension", "onec", "--dynamic", "--warnings-as-errors"],
            ["-Extension", "onec", "-Dynamic+", "-WarningsAsErrors"],
        ),
    ],
)
def test_build_1c_args(argv, tail, ib, tmp_path):
    ns = _ns(*argv, ib=ib)
    assert UpdateDbAction().build_1c_args(ns, RunContext(tmp_path / "1cv8")) == [
        "DESIGNER", "/F", str(ib), "/DisableStartupDialogs", "/UpdateDBCfg", *tail,
    ]


@pytest.mark.parametrize("argv", [[], ["--extension", "onec"], ["--all-extensions"]])
def test_validate_ok(argv, ib):
    UpdateDbAction().validate(_ns(*argv, ib=ib))


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (["--extension", "onec", "--all-extensions"], "взаимоисключающие"),
        (["--extension", " "], "не может быть пустым"),
    ],
)
def test_validate_errors(argv, message, ib):
    with pytest.raises(OneCOpsError, match=message):
        UpdateDbAction().validate(_ns(*argv, ib=ib))


def test_cli_changes(cli, mocker, caplog):
    out = "Новый объект: Справочник.Номенклатура\r\nОбновление конфигурации успешно завершено"
    run = mocker.patch("subprocess.run", side_effect=_fake_run(0, out))
    with caplog.at_level("INFO"):
        assert cli("update-db") == 0
    assert "/UpdateDBCfg" in run.call_args.args[0]
    assert "удалены из БД вместе с данными" in caplog.text
    assert "Конфигурация БД обновлена" in caplog.text


def test_cli_no_changes(cli, mocker, caplog):
    mocker.patch("subprocess.run", side_effect=_fake_run(0, ""))
    with caplog.at_level("INFO"):
        assert cli("update-db") == 0
    assert "Изменений нет" in caplog.text


def test_cli_failure_shows_1c_text(cli, mocker, caplog):
    mocker.patch("subprocess.run", side_effect=_fake_run(1, "Ошибка обновления структуры"))
    assert cli("update-db", "--warnings-as-errors") == 1
    assert "Ошибка обновления структуры" in caplog.text
    assert "Конфигурация БД обновлена" not in caplog.text


def test_cli_dry_run(cli, mocker, caplog):
    run = mocker.patch("subprocess.run")
    with caplog.at_level("INFO"):
        assert cli("--dry-run", "update-db", "--dynamic") == 0
    run.assert_not_called()
    assert "-Dynamic+" in caplog.text
    assert "Изменений нет" not in caplog.text
