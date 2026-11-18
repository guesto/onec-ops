"""Тесты команды install-skill."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from onec_ops import skill_install
from onec_ops.cli import main

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def home(tmp_path, monkeypatch):
    """Пустой домашний каталог без переменных агентов."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    for variable in ("CLAUDE_CONFIG_DIR", "CODEX_HOME", "KIMI_CODE_HOME"):
        monkeypatch.delenv(variable, raising=False)
    return home


@pytest.fixture
def no_platform(mocker):
    """install-skill не ищет платформу 1С."""
    return mocker.patch("onec_ops.cli.check_environment", side_effect=AssertionError)


def _skill(path: Path) -> Path:
    return path / "skills" / "onec-ops"


def test_source_has_skill_files():
    source = skill_install.skill_source()
    for item in skill_install.SKILL_ITEMS:
        assert (source / item).exists()


def test_source_prefers_package_copy(tmp_path, mocker):
    package = tmp_path / "onec_ops"
    skill = package / "skill"
    (skill / "references").mkdir(parents=True)
    (skill / "agents").mkdir()
    (skill / "SKILL.md").write_text("x", encoding="utf-8")
    mocker.patch.object(skill_install, "__file__", str(package / "skill_install.py"))
    assert skill_install.skill_source() == skill.resolve()


def test_source_missing(tmp_path, mocker):
    mocker.patch.object(skill_install, "__file__", str(tmp_path / "pkg" / "skill_install.py"))
    with pytest.raises(skill_install.OneCOpsError, match="не найдены"):
        skill_install.skill_source()


def test_installs_into_detected_agents(home, no_platform, capsys):
    (home / ".claude").mkdir()
    (home / ".codex").mkdir()

    assert main(["install-skill"]) == 0

    for agent in (".claude", ".codex"):
        target = _skill(home / agent)
        assert (target / "SKILL.md").read_bytes() == (ROOT / "SKILL.md").read_bytes()
        assert (target / "references" / "commands.md").is_file()
        assert (target / "agents" / "openai.yaml").is_file()
    assert not (home / ".kimi-code").exists()
    assert "установлено:" in capsys.readouterr().out
    no_platform.assert_not_called()


def test_no_agents_found(home, no_platform):
    assert main(["install-skill"]) == 1


def test_explicit_agent_creates_home(home, no_platform):
    assert main(["install-skill", "--agent", "kimi", "--agent", "kimi"]) == 0
    assert (_skill(home / ".kimi-code") / "SKILL.md").is_file()


def test_agent_home_from_environment(home, tmp_path, monkeypatch, no_platform):
    codex_home = tmp_path / "codex-home"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    assert main(["install-skill", "--agent", "codex"]) == 0
    assert (_skill(codex_home) / "SKILL.md").is_file()


def test_project_install(home, tmp_path, no_platform):
    project = tmp_path / "project"
    (project / ".claude").mkdir(parents=True)
    (home / ".codex").mkdir()

    assert main(["install-skill", "--project", str(project)]) == 0

    assert (_skill(project / ".claude") / "SKILL.md").is_file()
    assert not (project / ".codex").exists()
    assert not (home / ".codex" / "skills").exists()


def test_opencode_home_install(home, no_platform):
    assert main(["install-skill", "--agent", "opencode"]) == 0
    assert (_skill(home / ".config" / "opencode") / "SKILL.md").is_file()


def test_opencode_detected_by_config_dir(home, no_platform):
    (home / ".config" / "opencode").mkdir(parents=True)
    assert main(["install-skill"]) == 0
    assert (_skill(home / ".config" / "opencode") / "SKILL.md").is_file()


def test_opencode_project_uses_dot_opencode(home, tmp_path, no_platform):
    project = tmp_path / "project"
    (project / ".opencode").mkdir(parents=True)

    assert main(["install-skill", "--project", str(project)]) == 0

    assert (_skill(project / ".opencode") / "SKILL.md").is_file()
    assert not (project / ".config").exists()


def test_project_missing(tmp_path, no_platform):
    assert main(["install-skill", "--project", str(tmp_path / "nope"), "--agent", "claude"]) == 1


def test_target_install_and_conflict(tmp_path, no_platform):
    target = tmp_path / "custom"
    assert main(["install-skill", "--target", str(target)]) == 0
    assert (target / "SKILL.md").is_file()
    assert main(["install-skill", "--target", str(target), "--agent", "claude"]) == 1


def test_update_replaces_stale_files_keeps_others(tmp_path, no_platform, capsys):
    target = tmp_path / "skill"
    main(["install-skill", "--target", str(target)])
    (target / "references" / "old.md").write_text("old", encoding="utf-8")
    (target / "SKILL.md").write_text("---\nname: onec-ops\n---\nold\n", encoding="utf-8")
    (target / "notes.txt").write_text("mine", encoding="utf-8")

    assert main(["install-skill", "--target", str(target)]) == 0

    assert not (target / "references" / "old.md").exists()
    assert (target / "SKILL.md").read_bytes() == (ROOT / "SKILL.md").read_bytes()
    assert (target / "notes.txt").read_text(encoding="utf-8") == "mine"
    capsys.readouterr()
    assert main(["install-skill", "--target", str(target)]) == 0
    assert "актуально:" in capsys.readouterr().out


def test_replaces_file_in_place_of_directory(tmp_path, no_platform):
    target = tmp_path / "skill"
    target.mkdir()
    (target / "SKILL.md").write_text('name: "onec-ops"\n', encoding="utf-8")
    (target / "references").write_text("file", encoding="utf-8")
    assert main(["install-skill", "--target", str(target)]) == 0
    assert (target / "references").is_dir()


def test_dry_run_writes_nothing(tmp_path, no_platform, capsys):
    target = tmp_path / "skill"
    assert main(["install-skill", "--target", str(target), "--dry-run"]) == 0
    assert not target.exists()
    assert "будет установлено:" in capsys.readouterr().out


def test_global_dry_run(tmp_path, no_platform):
    target = tmp_path / "skill"
    assert main(["--dry-run", "install-skill", "--target", str(target)]) == 0
    assert not target.exists()


def test_refuses_other_skill(tmp_path, no_platform):
    target = tmp_path / "skill"
    target.mkdir()
    (target / "SKILL.md").write_text("---\nname: other\n---\n", encoding="utf-8")
    assert main(["install-skill", "--target", str(target)]) == 1
    assert (target / "SKILL.md").read_text(encoding="utf-8").startswith("---\nname: other")


def test_refuses_non_empty_foreign_directory(tmp_path, no_platform):
    target = tmp_path / "skill"
    target.mkdir()
    (target / "data.txt").write_text("x", encoding="utf-8")
    assert main(["install-skill", "--target", str(target)]) == 1


def test_refuses_file_target(tmp_path, no_platform):
    target = tmp_path / "skill"
    target.write_text("x", encoding="utf-8")
    assert main(["install-skill", "--target", str(target)]) == 1


def test_empty_directory_is_filled(tmp_path, no_platform):
    target = tmp_path / "skill"
    target.mkdir()
    assert main(["install-skill", "--target", str(target)]) == 0
    assert (target / "SKILL.md").is_file()


def test_copy_error(tmp_path, mocker, no_platform):
    mocker.patch.object(skill_install.shutil, "copy2", side_effect=OSError("disk full"))
    assert main(["install-skill", "--target", str(tmp_path / "skill")]) == 1


def _symlinks_supported(tmp_path: Path) -> bool:
    try:
        os.symlink(tmp_path, tmp_path / "probe")
    except (OSError, NotImplementedError):
        return False
    return True


def test_skips_symlinked_dev_install(tmp_path, no_platform, caplog, capsys):
    if not _symlinks_supported(tmp_path):
        pytest.skip("симлинки недоступны")
    target = tmp_path / "skill"
    target.mkdir()
    (target / "SKILL.md").symlink_to(ROOT / "SKILL.md")

    assert main(["install-skill", "--target", str(target)]) == 0
    assert (target / "SKILL.md").is_symlink()
    assert "git pull" in caplog.text
    assert main(["install-skill", "--target", str(target), "--check"]) == 0
    assert "ссылки на репозиторий:" in capsys.readouterr().out


def test_check_reports_status(home, no_platform, capsys):
    (home / ".claude").mkdir()
    (home / ".codex").mkdir()
    main(["install-skill", "--agent", "claude"])
    capsys.readouterr()

    assert main(["install-skill", "--check"]) == 1
    out = capsys.readouterr().out
    assert f"актуально: {_skill(home / '.claude')}" in out
    assert f"не установлен: {_skill(home / '.codex')}" in out

    main(["install-skill", "--agent", "codex"])
    (_skill(home / ".codex") / "references" / "commands.md").write_text("x", encoding="utf-8")
    capsys.readouterr()
    assert main(["install-skill", "--check"]) == 1
    assert f"устарело: {_skill(home / '.codex')}" in capsys.readouterr().out

    main(["install-skill", "--agent", "codex"])
    assert main(["install-skill", "--check"]) == 0


@pytest.mark.parametrize(
    "change",
    [
        lambda path: (path / "references" / "extra.md").write_text("x", encoding="utf-8"),
        lambda path: (path / "references" / "commands.md").unlink(),
        lambda path: (path / "agents" / "openai.yaml").write_text("x", encoding="utf-8"),
        lambda path: (path / "SKILL.md").unlink(),
    ],
    ids=["extra", "missing", "changed-nested", "no-skill-md"],
)
def test_is_current_detects_changes(tmp_path, no_platform, change):
    target = tmp_path / "skill"
    main(["install-skill", "--target", str(target)])
    source = skill_install.skill_source()
    assert skill_install.is_current(source, target)
    change(target)
    assert not skill_install.is_current(source, target)


def test_is_current_missing_directory(tmp_path):
    target = tmp_path / "skill"
    target.mkdir()
    (target / "SKILL.md").write_bytes((ROOT / "SKILL.md").read_bytes())
    assert not skill_install.is_current(skill_install.skill_source(), target)


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as error:
        main(["--version"])
    assert error.value.code == 0
    assert capsys.readouterr().out.startswith("onec-ops ")


def test_version_unknown(mocker):
    from onec_ops import cli

    mocker.patch.object(cli, "version", side_effect=cli.PackageNotFoundError)
    assert cli._version() == "unknown"
