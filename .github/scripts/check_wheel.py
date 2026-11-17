"""Проверяет состав wheel: пакет onec_ops и навык, без тестов и данных."""

from __future__ import annotations

import sys
import zipfile

REQUIRED = (
    "onec_ops/cli.py",
    "onec_ops/skill/SKILL.md",
    "onec_ops/skill/references/commands.md",
    "onec_ops/skill/agents/openai.yaml",
)
FORBIDDEN_PREFIXES = ("scripts/", "tests/", "inputs/", "outputs/", "docs/")


def main(path: str) -> int:
    names = zipfile.ZipFile(path).namelist()
    errors = [f"нет файла {name}" for name in REQUIRED if name not in names]
    errors += [f"лишний файл {name}" for name in names if name.startswith(FORBIDDEN_PREFIXES)]
    for error in errors:
        print(f"::error::{path}: {error}")
    print(f"{path}: {len(names)} файлов, ошибок: {len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
