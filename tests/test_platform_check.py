"""Тесты проверки окружения."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.lib.exceptions import PlatformNotFound, XvfbNotAvailable
from scripts.lib.platform_check import check_environment
from scripts.lib.runner import RunContext


def _platform(tmp_path: Path) -> Path:
    platform = tmp_path / "1cv8"
    platform.touch()
    platform.chmod(0o755)
    return platform


def test_missing_platform_raises_platform_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.lib.platform_check.sys.platform", "win32")

    with pytest.raises(PlatformNotFound):
        check_environment(RunContext(tmp_path / "missing"))


def test_linux_without_display_or_xvfb_raises(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.lib.platform_check.sys.platform", "linux")
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.setattr("scripts.lib.platform_check.shutil.which", lambda name: None)

    with pytest.raises(XvfbNotAvailable, match="Установите xvfb или задайте DISPLAY"):
        check_environment(RunContext(_platform(tmp_path)))


def test_valid_windows_environment_passes(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.lib.platform_check.sys.platform", "win32")

    check_environment(RunContext(_platform(tmp_path)))
