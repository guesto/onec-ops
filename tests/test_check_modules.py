"""Тесты check-modules и check-config."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.actions.check_modules import CheckConfigAction, CheckModulesAction
from scripts.lib.exceptions import OneCOpsError
from scripts.lib.runner import RunContext
from scripts.onec_ops import build_parser, main

ALL_MODES = [
    "-ThinClient",
    "-WebClient",
    "-Server",
    "-ExternalConnection",
    "-ThickClientOrdinaryApplication",
]
ACTIONS = {"check-modules": CheckModulesAction, "check-config": CheckConfigAction}
CHECK_ARGS = {
    "check-modules": ["/CheckModules"],
    "check-config": ["/CheckConfig", "-ConfigLogIntegrity", "-IncorrectReferences"],
}
FINDINGS = "{Справочник.Клиенты.МодульОбъекта(5,1)}: Ожидается имя\n<<?>>КонецПроцедуры (Проверка: Сервер)"


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


def _args(name, ib, *argv):
    ns = build_parser().parse_args([name, *argv])
    ns.ib = ib
    return ACTIONS[name]().build_1c_args(ns, RunContext(Path("1cv8")))


@pytest.mark.parametrize("name", ACTIONS)
def test_all_modes_by_default(name, ib):
    assert _args(name, ib) == [
        "DESIGNER", "/F", str(ib), "/DisableStartupDialogs", *CHECK_ARGS[name], *ALL_MODES,
    ]


@pytest.mark.parametrize("name", ACTIONS)
def test_selected_modes_keep_fixed_order(name, ib):
    args = _args(name, ib, "--mode", "server", "--mode", "thin-client", "--mode", "server")

    assert args[4:] == [*CHECK_ARGS[name], "-ThinClient", "-Server"]


@pytest.mark.parametrize("name", ACTIONS)
def test_extended_and_extension(name, ib):
    args = _args(name, ib, "--mode", "server", "--extended", "--extension", "Расш")

    assert args[-4:] == ["-Server", "-ExtendedModulesCheck", "-Extension", "Расш"]


@pytest.mark.parametrize("name", ACTIONS)
def test_all_extensions(name, ib):
    assert _args(name, ib, "--all-extensions")[-1] == "-AllExtensions"


def test_unknown_mode_rejected():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["check-modules", "--mode", "mobile"])


@pytest.mark.parametrize("name", ACTIONS)
@pytest.mark.parametrize(
    "argv", [["--extension", " "], ["--extension", "A", "--all-extensions"]], ids=["empty", "both"]
)
def test_validate_extension_target(name, argv, ib):
    ns = build_parser().parse_args([name, *argv])
    ns.ib = ib

    with pytest.raises(OneCOpsError):
        ACTIONS[name]().validate(ns)


@pytest.mark.parametrize("name", ACTIONS)
def test_success(name, cli, mocker, caplog):
    run = mocker.patch(
        "scripts.lib.runner._execute", side_effect=_fake_run(0, "Синтаксических ошибок не обнаружено!")
    )
    caplog.set_level("INFO")

    assert cli(name) == 0
    assert run.called
    assert "Проверка пройдена: Синтаксических ошибок не обнаружено!" in caplog.text


@pytest.mark.parametrize("name", ACTIONS)
def test_findings_return_one_with_full_text(name, cli, mocker, caplog):
    mocker.patch("scripts.lib.runner._execute", side_effect=_fake_run(101, FINDINGS))

    assert cli(name) == 1
    errors = [r.getMessage() for r in caplog.records if r.levelname == "ERROR"]
    assert errors == [f"Найдены замечания 1С:\n{FINDINGS}"]


@pytest.mark.parametrize("name", ACTIONS)
def test_other_code_is_regular_failure(name, cli, mocker, caplog):
    mocker.patch("scripts.lib.runner._execute", side_effect=_fake_run(1, "Расширение не найдено."))

    assert cli(name) == 1
    errors = [r.getMessage() for r in caplog.records if r.levelname == "ERROR"]
    assert errors == ["1С завершилась с ненулевым кодом: 1\nРасширение не найдено."]


def test_code_101_stays_regular_failure_in_other_commands(cli, mocker, caplog):
    mocker.patch("scripts.lib.runner._execute", side_effect=_fake_run(101, "Текст"))

    assert cli("update-db") == 1
    assert "1С завершилась с ненулевым кодом: 101" in caplog.text
    assert "Найдены замечания" not in caplog.text


@pytest.mark.parametrize("name", ACTIONS)
def test_dry_run_does_not_start_1c(name, cli, mocker):
    run = mocker.patch("scripts.lib.runner._execute")

    assert cli("--dry-run", name) == 0
    run.assert_not_called()
