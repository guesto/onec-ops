"""Тесты конфига и выбора платформы 1С."""

from __future__ import annotations

from pathlib import Path

import pytest

from onec_ops.cli import main
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


def _install(root: Path, version: str, executable: Path, *, mode: int = 0o755) -> Path:
    path = root / version / executable
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")
    path.chmod(mode)
    return path


@pytest.fixture
def platform_root(monkeypatch, tmp_path):
    """Подменяет каталог установки платформы для текущей ОС на временный."""
    attr = "_WINDOWS_PLATFORM_ROOT" if config.sys.platform == "win32" else "_LINUX_PLATFORM_ROOT"
    monkeypatch.setattr(config, attr, tmp_path)
    return tmp_path


@pytest.mark.parametrize(
    ("platform", "attr", "executable"),
    [
        ("linux", "_LINUX_PLATFORM_ROOT", Path("1cv8")),
        ("win32", "_WINDOWS_PLATFORM_ROOT", Path("bin") / "1cv8.exe"),
    ],
)
def test_default_platform_is_latest_installed(monkeypatch, tmp_path, platform, attr, executable):
    monkeypatch.setattr("onec_ops.lib.config.sys.platform", platform)
    monkeypatch.setattr(config, attr, tmp_path)
    _install(tmp_path, "8.5.1.1343", executable)
    latest = _install(tmp_path, "8.5.4.2072", executable)
    _install(tmp_path, "8.3.27.1859", executable)
    assert resolve_platform(None, {}) == latest


def test_versions_compared_numerically(platform_root):
    root = platform_root
    executable = config._platform_layout()[1]
    _install(root, "8.5.1.999", executable)
    latest = _install(root, "8.5.1.1529", executable)
    assert resolve_platform(None, {}) == latest


def test_skips_dirs_without_platform(platform_root):
    root = platform_root
    executable = config._platform_layout()[1]
    latest = _install(root, "8.5.1.1529", executable)
    (root / "8.5.4.2072").mkdir()
    (root / "conf").mkdir()
    _install(root, "9.0.0.1-beta", executable)
    assert resolve_platform(None, {}) == latest


@pytest.mark.skipif(config.sys.platform == "win32", reason="права на исполнение только в POSIX")
def test_skips_not_executable_platform(platform_root):
    executable = config._platform_layout()[1]
    latest = _install(platform_root, "8.5.1.1529", executable)
    _install(platform_root, "8.5.4.2072", executable, mode=0o644)
    assert resolve_platform(None, {}) == latest


def test_logs_chosen_version(platform_root, caplog):
    _install(platform_root, "8.5.4.2072", config._platform_layout()[1])
    with caplog.at_level("INFO", logger="onec_ops.lib.config"):
        resolve_platform(None, {})
    assert "8.5.4.2072" in caplog.text


def test_no_platform_installed_returns_placeholder(platform_root):
    path = resolve_platform(None, {})
    assert path == platform_root / "<версия>" / config._platform_layout()[1]
    assert not path.exists()


def test_missing_platform_root(monkeypatch, tmp_path):
    attr = "_WINDOWS_PLATFORM_ROOT" if config.sys.platform == "win32" else "_LINUX_PLATFORM_ROOT"
    monkeypatch.setattr(config, attr, tmp_path / "missing")
    assert not resolve_platform(None, {}).exists()


def test_cli_reports_missing_platform(platform_root, caplog):
    missing_config = platform_root / "missing.toml"
    args = ["create-ib", "--config", str(missing_config), "--type", "file"]
    assert main([*args, "--path", str(platform_root / "ib")]) == 1
    assert "Платформа 1С не найдена" in caplog.text
    assert "<версия>" in caplog.text


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
