"""Команда install-skill: копия навыка в каталоги агентов."""

from __future__ import annotations

import argparse
import filecmp
import logging
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from onec_ops.lib.exceptions import OneCOpsError

logger = logging.getLogger(__name__)

NAME = "install-skill"
SKILL_NAME = "onec-ops"
SKILL_ITEMS = ("SKILL.md", "references", "agents")

# Агент: (переменная окружения с домашним каталогом, каталог по умолчанию в HOME).
AGENTS: dict[str, tuple[str | None, str]] = {
    "claude": ("CLAUDE_CONFIG_DIR", ".claude"),
    "codex": ("CODEX_HOME", ".codex"),
    "kimi": ("KIMI_CODE_HOME", ".kimi-code"),
    "opencode": (None, ".config/opencode"),
    "agents": (None, ".agents"),
}

# Каталог агента внутри проекта, если он не совпадает с каталогом в HOME.
PROJECT_DIRS: dict[str, str] = {"opencode": ".opencode"}

_NAME_LINE = re.compile(r'^name:\s*"?([^"\n]+?)"?\s*$', re.MULTILINE)


@dataclass(frozen=True)
class Target:
    """Каталог навыка у одного агента."""

    agent: str
    path: Path


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    """Регистрирует install-skill в CLI."""
    parser = subparsers.add_parser(
        NAME,
        help="Установить или обновить Agent Skill",
        description=(
            "Копирует навык onec-ops (SKILL.md, references, agents) из установленного "
            "пакета в каталоги агентов. Без --agent выбирает агентов, чьи каталоги уже есть."
        ),
    )
    parser.add_argument(
        "--agent",
        action="append",
        choices=sorted(AGENTS),
        help="Агент: claude, codex, kimi, opencode, agents (~/.agents). Можно повторять",
    )
    place = parser.add_mutually_exclusive_group()
    place.add_argument(
        "--project", type=Path, help="Установить в проект: <каталог>/.<агент>/skills/onec-ops"
    )
    place.add_argument("--target", type=Path, help="Явный каталог навыка")
    parser.add_argument(
        "--check", action="store_true", help="Только проверить, актуальны ли установленные копии"
    )
    parser.add_argument(
        "--dry-run", action="store_true", default=argparse.SUPPRESS, help="Ничего не менять"
    )


def skill_source() -> Path:
    """Каталог с файлами навыка: внутри пакета или в корне репозитория."""
    package_dir = Path(__file__).resolve().parent
    for candidate in (package_dir / "skill", package_dir.parent):
        if all((candidate / item).exists() for item in SKILL_ITEMS):
            return candidate
    raise OneCOpsError("Файлы навыка не найдены в пакете onec-ops. Переустановите пакет.")


def _agent_home(agent: str) -> Path:
    variable, default = AGENTS[agent]
    value = os.environ.get(variable) if variable else None
    return Path(value).expanduser() if value else Path.home() / default


def resolve_targets(ns: argparse.Namespace) -> list[Target]:
    """Выбирает каталоги для установки или проверки."""
    if ns.target is not None:
        if ns.agent:
            raise OneCOpsError("--target нельзя сочетать с --agent.")
        return [Target("target", ns.target.expanduser().resolve())]
    if ns.project is not None:
        project = ns.project.expanduser().resolve()
        if not project.is_dir():
            raise OneCOpsError(f"Каталог проекта не найден: {project}")
        homes = {agent: project / PROJECT_DIRS.get(agent, AGENTS[agent][1]) for agent in AGENTS}
    else:
        homes = {agent: _agent_home(agent) for agent in AGENTS}
    agents = list(dict.fromkeys(ns.agent or []))
    if not agents:
        agents = [agent for agent, home in homes.items() if home.is_dir()]
        if not agents:
            where = "в проекте" if ns.project is not None else "в домашнем каталоге"
            raise OneCOpsError(
                f"Каталоги агентов {where} не найдены. Укажите --agent claude, codex, kimi, "
                "opencode или agents."
            )
    return [Target(agent, homes[agent] / "skills" / SKILL_NAME) for agent in agents]


def _is_linked(path: Path) -> bool:
    return path.is_symlink() or any((path / item).is_symlink() for item in SKILL_ITEMS)


def _check_foreign(path: Path) -> None:
    """Не даёт перезаписать чужой каталог."""
    if not path.exists():
        return
    if not path.is_dir():
        raise OneCOpsError(f"{path} существует и не является каталогом.")
    skill = path / "SKILL.md"
    if skill.is_file():
        match = _NAME_LINE.search(skill.read_text(encoding="utf-8", errors="replace"))
        if match and match.group(1).strip() == SKILL_NAME:
            return
        raise OneCOpsError(f"{path} содержит другой навык, не onec-ops.")
    if any(path.iterdir()):
        raise OneCOpsError(f"{path} не пуст и не похож на навык onec-ops.")


def _same_tree(left: Path, right: Path) -> bool:
    if left.is_file() or right.is_file():
        return left.is_file() and right.is_file() and filecmp.cmp(left, right, shallow=False)
    if not right.is_dir():
        return False
    compare = filecmp.dircmp(left, right, ignore=["__pycache__"])
    if compare.left_only or compare.right_only or compare.funny_files:
        return False
    _, mismatch, errors = filecmp.cmpfiles(left, right, compare.common_files, shallow=False)
    if mismatch or errors:
        return False
    return all(_same_tree(left / name, right / name) for name in compare.common_dirs)


def is_current(source: Path, path: Path) -> bool:
    """Совпадает ли копия навыка с файлами пакета."""
    return all(_same_tree(source / item, path / item) for item in SKILL_ITEMS)


def _copy(source: Path, path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for item in SKILL_ITEMS:
        src, dst = source / item, path / item
        if dst.is_dir():
            shutil.rmtree(dst)
        elif dst.exists():
            dst.unlink()
        if src.is_dir():
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(src, dst)


def _check(source: Path, targets: list[Target]) -> int:
    code = 0
    for target in targets:
        if not target.path.exists():
            status, code = "не установлен", 1
        elif _is_linked(target.path):
            status = "ссылки на репозиторий"
        elif is_current(source, target.path):
            status = "актуально"
        else:
            status, code = "устарело", 1
        print(f"{status}: {target.path}")
    return code


def run(ns: argparse.Namespace) -> int:
    """Устанавливает навык или проверяет копии."""
    source = skill_source()
    targets = resolve_targets(ns)
    if ns.check:
        return _check(source, targets)
    dry_run = getattr(ns, "dry_run", False)
    for target in targets:
        if _is_linked(target.path):
            logger.warning(
                "%s: ссылки на репозиторий, навык обновляется через git pull — пропущено.",
                target.path,
            )
            continue
        _check_foreign(target.path)
        if target.path.exists() and is_current(source, target.path):
            print(f"актуально: {target.path}")
            continue
        if dry_run:
            print(f"будет установлено: {target.path}")
            continue
        try:
            _copy(source, target.path)
        except OSError as error:
            raise OneCOpsError(f"Не удалось скопировать навык в {target.path}: {error}") from error
        print(f"установлено: {target.path}")
    return 0
