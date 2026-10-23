"""Тесты конфига и выбора платформы 1С."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.lib import config
from scripts.lib.config import load_config, resolve_platform

CLI = Path("/cli/1cv8")
ENV = "/env/1cv8"
CONFIG = {"platform": "/config/1cv8"}


@pytest.fixture(autouse=True)
def _no_platform_env(monkeypatch):
    monkeypatch.delenv("ONEC_OPS_PLATFORM", raising=False)


def test_cli_wins_over_env_and_config(monkeypatch):
    monkeypatch.setenv("ONEC_OPS_PLATFORM", ENV)
    assert resolve_platform(CLI, CONFIG) == CLI


def test_env_wins_over_config(monkeypatch):
    monkeypatch.setenv("ONEC_OPS_PLATFORM", ENV)
    assert resolve_platform(None, CONFIG) == Path(ENV)


def test_config_wins_over_default():
    assert resolve_platform(None, CONFIG) == Path("/config/1cv8")


def test_empty_env_is_ignored(monkeypatch):
    monkeypatch.setenv("ONEC_OPS_PLATFORM", "")
    assert resolve_platform(None, CONFIG) == Path("/config/1cv8")


@pytest.mark.parametrize(
    ("platform", "expected"),
    [("linux", config._LINUX_PLATFORM), ("win32", config._WINDOWS_PLATFORM)],
)
def test_default_platform(monkeypatch, platform, expected):
    monkeypatch.setattr("scripts.lib.config.sys.platform", platform)
    assert resolve_platform(None, {}) == expected


def test_load_config_missing_file(tmp_path):
    assert load_config(tmp_path / "missing.toml") == {}


def test_load_config_explicit_path(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('platform = "/opt/1cv8/x86_64/8.3.25.1374/1cv8"\n', encoding="utf-8")
    assert load_config(path) == {"platform": "/opt/1cv8/x86_64/8.3.25.1374/1cv8"}


def test_load_config_default_location(tmp_path, monkeypatch):
    (tmp_path / "config.toml").write_text('platform = "/default/1cv8"\n', encoding="utf-8")
    monkeypatch.setattr("scripts.lib.config.user_config_dir", lambda name: str(tmp_path))
    assert load_config(None) == {"platform": "/default/1cv8"}


def test_cli_uses_config_platform(tmp_path, mocker, caplog):
    from scripts.onec_ops import main

    platform = tmp_path / "1cv8"
    platform.touch()
    platform.chmod(0o755)
    path = tmp_path / "config.toml"
    path.write_text(f'platform = "{platform}"\n', encoding="utf-8")
    mocker.patch("scripts.onec_ops.check_environment")
    mocker.patch("scripts.lib.runner.shutil.which", return_value="/usr/bin/xvfb-run")
    with caplog.at_level("INFO"):
        assert main(["--config", str(path), "--dry-run", "create-ib", "--type", "file",
                     "--path", str(tmp_path / "ib")]) == 0
    assert str(platform) in caplog.text
