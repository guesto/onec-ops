"""Проверка дрейфа между CLI и Agent Skill."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from scripts.actions import get_actions

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "SKILL.md"
REFERENCES = ROOT / "references"
SKILL_PACKAGE = [SKILL, *sorted(REFERENCES.glob("*.md"))]
ACTION_NAMES = [action.name for action in get_actions()]
_LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")


def _frontmatter() -> dict[str, str]:
    text = SKILL.read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
    assert match, "SKILL.md должен начинаться с YAML frontmatter"
    fields = {}
    for line in match.group(1).splitlines():
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields


def test_frontmatter_name():
    assert _frontmatter()["name"] == "onec-ops"


def test_frontmatter_description():
    description = _frontmatter()["description"]
    assert description
    assert len(description) <= 1024
    lowered = description.lower()
    for match in re.finditer("клиент-серверн", lowered):
        assert lowered[: match.start()].endswith("не для "), "навык не поддерживает клиент-серверные ИБ"


def test_skill_is_compact():
    assert len(SKILL.read_text(encoding="utf-8").splitlines()) <= 250


@pytest.mark.parametrize("name", ACTION_NAMES)
def test_action_in_skill(name):
    assert f"`onec-ops {name}" in SKILL.read_text(encoding="utf-8")


@pytest.mark.parametrize("name", ACTION_NAMES)
def test_action_in_commands_reference(name):
    text = (REFERENCES / "commands.md").read_text(encoding="utf-8")
    assert re.search(rf"^## {re.escape(name)}$", text, re.MULTILINE)


@pytest.mark.parametrize("path", SKILL_PACKAGE, ids=lambda path: path.name)
def test_links_stay_inside_skill_package(path):
    package_dirs = {REFERENCES.resolve(), (ROOT / "agents").resolve()}
    for target in _LINK.findall(path.read_text(encoding="utf-8")):
        if re.match(r"[a-z]+://", target):
            continue
        resolved = (path.parent / target).resolve()
        assert resolved.exists(), f"{path.name}: битая ссылка {target}"
        assert resolved == SKILL.resolve() or resolved.parent in package_dirs, (
            f"{path.name}: ссылка {target} ведёт за пределы пакета навыка"
        )
