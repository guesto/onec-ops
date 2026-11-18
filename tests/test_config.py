"""Тесты конфига и выбора платформы 1С."""

from __future__ import annotations

from pathlib import Path

import pytest

from onec_ops.lib import config
from onec_ops.lib.config import load_config, resolve_platform

CLI = Path("/cli/1cv8")
ENV = "/env/1cv8"
CONFIG = {"platform": "/config/1cv8"}


@pytest.fixture(autouse=True)
def _no_platform_env(monkeypatch):
    monkeypatch.delenv("ONEC_OPS_PLATFORM", raising=False)


def test_cli_wins_over_env_and_config(monkeypatch):
    monkeypatch.setenv("ONEC_OPS_PLATFORM", ENV)
    assert resolve_platform(CLI, CONFIG) == CLI.absolute()


def test_env_wins_over_config(monkeypatch):
    monkeypatch.setenv("ONEC_OPS_PLATFORM", ENV)
    assert resolve_platform(None, CONFIG) == Path(ENV).absolute()


def test_config_wins_over_default():
    assert resolve_platform(None, CONFIG) == Path("/config/1cv8").absolute()


def test_empty_env_is_ignored(monkeypatch):
    monkeypatch.setenv("ONEC_OPS_PLATFORM", "")
    assert resolve_platform(None, CONFIG) == Path("/config/1cv8").absolute()


@pytest.mark.parametrize(
    ("platform", "expected"),
    [("linux", config._LINUX_PLATFORM), ("win32", config._WINDOWS_PLATFORM)],
)
def test_default_platform(monkeypatch, platform, expected):
    monkeypatch.setattr("onec_ops.lib.config.sys.platform", platform)
    assert resolve_platform(None, {}) == expected


def test_load_config_missing_file(tmp_path):
    assert load_config(tmp_path / "missing.toml") == {}


def test_load_config_explicit_path(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('platform = "/opt/1cv8/x86_64/8.3.25.1374/1cv8"\n', encoding="utf-8")
    assert load_config(path) == {"platform": "/opt/1cv8/x86_64/8.3.25.1374/1cv8"}


def test_load_config_default_location(tmp_path, monkeypatch):
    (tmp_path / "config.toml").write_text('platform = "/default/1cv8"\n', encoding="utf-8")
    monkeypatch.setattr("onec_ops.lib.config.user_config_dir", lambda name: str(tmp_path))
    assert load_config(None) == {"platform": "/default/1cv8"}


def test_cli_uses_config_platform(tmp_path, mocker, caplog):
    from onec_ops.cli import main

    platform = tmp_path / "1cv8"
    platform.touch()
    platform.chmod(0o755)
    path = tmp_path / "config.toml"
    path.write_text(f"platform = '{platform}'\n", encoding="utf-8")
    mocker.patch("onec_ops.cli.check_environment")
    mocker.patch("onec_ops.lib.runner.shutil.which", return_value="/usr/bin/xvfb-run")
    with caplog.at_level("INFO"):
        assert (
            main(
                [
                    "--config",
                    str(path),
                    "--dry-run",
                    "create-ib",
                    "--type",
                    "file",
                    "--path",
                    str(tmp_path / "ib"),
                ]
            )
            == 0
        )
    assert repr(str(platform)) in caplog.text


@pytest.mark.parametrize(
    "source, message",
    [
        (b"platform = [\n", "Не удалось загрузить конфигурационный файл"),
        (b"\xff", "Не удалось загрузить конфигурационный файл"),
        (b"platform = 42\n", "platform"),
        (b"platform = false\n", "platform"),
        (b"platform = []\n", "platform"),
        (b"platform = {}\n", "platform"),
    ],
)
def test_cli_invalid_config_returns_error_without_starting_platform(
    tmp_path,
    mocker,
    caplog,
    source,
    message,
):
    from onec_ops.cli import main

    config_path = tmp_path / "config.toml"
    config_path.write_bytes(source)
    run = mocker.patch("onec_ops.cli.run_1c")
    check = mocker.patch("onec_ops.cli.check_environment")
    ib = tmp_path / "ib"

    assert (
        main(["--config", str(config_path), "create-ib", "--type", "file", "--path", str(ib)]) == 1
    )

    assert str(config_path) in caplog.text
    assert message in caplog.text
    assert "Traceback" not in caplog.text
    assert not ib.exists()
    check.assert_not_called()
    run.assert_not_called()


def test_cli_config_path_is_directory_returns_error(tmp_path, mocker, caplog):
    from onec_ops.cli import main

    run = mocker.patch("onec_ops.cli.run_1c")
    assert (
        main(
            [
                "--config",
                str(tmp_path),
                "create-ib",
                "--type",
                "file",
                "--path",
                str(tmp_path / "ib"),
            ]
        )
        == 1
    )
    assert "Не удалось загрузить конфигурационный файл" in caplog.text
    assert str(tmp_path) in caplog.text
    run.assert_not_called()


def test_default_config_path_uses_platformdirs(tmp_path, monkeypatch):
    monkeypatch.setattr("onec_ops.lib.config.user_config_dir", lambda name: str(tmp_path / name))
    assert config.default_config_path() == tmp_path / "onec-ops" / "config.toml"


def test_describe_config_default_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("onec_ops.lib.config.user_config_dir", lambda name: str(tmp_path))
    text = config.describe_config(None)
    assert str(tmp_path / "config.toml") in text
    assert "по умолчанию" in text
    assert "не найден" in text


def test_describe_config_explicit_found(tmp_path):
    path = tmp_path / "my.toml"
    path.write_text("", encoding="utf-8")
    text = config.describe_config(path)
    assert "--config" in text
    assert str(path) in text
    assert "не найден" not in text


def test_platform_not_found_reports_config_path(tmp_path, monkeypatch, caplog):
    from onec_ops.cli import main

    monkeypatch.setattr("onec_ops.lib.config.user_config_dir", lambda name: str(tmp_path))
    code = main(
        [
            "--platform",
            str(tmp_path / "missing"),
            "create-ib",
            "--type",
            "file",
            "--path",
            str(tmp_path / "ib"),
        ]
    )
    assert code == 1
    assert "Платформа 1С не найдена" in caplog.text
    assert str(tmp_path / "config.toml") in caplog.text


def test_dry_run_reports_config_path(tmp_path, monkeypatch, caplog):
    from onec_ops.cli import main

    platform = tmp_path / "1cv8"
    platform.touch()
    platform.chmod(0o755)
    config_path = tmp_path / "config.toml"
    config_path.write_text(f"platform = '{platform}'\n", encoding="utf-8")
    monkeypatch.setattr("onec_ops.lib.config.user_config_dir", lambda name: str(tmp_path))
    monkeypatch.setenv("DISPLAY", ":99")
    with caplog.at_level("INFO"):
        code = main(["--dry-run", "create-ib", "--type", "file", "--path", str(tmp_path / "ib")])
    assert code == 0
    assert f"{config_path} — найден" in caplog.text


def test_help_shows_default_config_path(tmp_path, monkeypatch, capsys):
    from onec_ops.cli import build_parser

    monkeypatch.setattr("onec_ops.lib.config.user_config_dir", lambda name: str(tmp_path))
    monkeypatch.setenv("COLUMNS", "500")
    build_parser().print_help()
    assert str(tmp_path / "config.toml") in capsys.readouterr().out
